// Independent implementation of the written methods in Valenza et al. (2020).
// No author code was consulted. GDAL supplies file I/O, not the analysis.
#include <gdal_priv.h>
#include <ogr_spatialref.h>
#include <cpl_conv.h>
#include <algorithm>
#include <array>
#include <cmath>
#include <cstdint>
#include <filesystem>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <limits>
#include <map>
#include <memory>
#include <sstream>
#include <stdexcept>
#include <string>
#include <vector>
namespace fs = std::filesystem;
const double NaN = std::numeric_limits<double>::quiet_NaN();
using Dataset = std::unique_ptr<GDALDataset, void(*)(GDALDataset*)>;

void require(bool ok, const std::string& message) {
    if (!ok) throw std::runtime_error(message);
}
Dataset open(const std::string& path) {
    auto* ds = static_cast<GDALDataset*>(GDALOpen(path.c_str(), GA_ReadOnly));
    require(ds != nullptr, "Cannot open " + path);
    return Dataset(ds, [](GDALDataset* p) { GDALClose(p); });
}
std::vector<std::string> split(std::string text, char delimiter) {
    if (!text.empty() && text.back() == '\r') text.pop_back();
    std::stringstream stream(text);
    std::vector<std::string> out;
    std::string field;
    while (std::getline(stream, field, delimiter)) out.push_back(field);
    return out;
}
double quantile(std::vector<double> values, double p) {
    require(p >= 0 && p <= 1, "Quantile probability outside [0,1]");
    values.erase(std::remove_if(values.begin(), values.end(),
                 [](double x) { return !std::isfinite(x); }), values.end());
    if (values.empty()) return NaN;
    const double index = (values.size() - 1) * p;
    const size_t lo = static_cast<size_t>(index), hi = static_cast<size_t>(std::ceil(index));
    std::nth_element(values.begin(), values.begin() + lo, values.end());
    const double a = values[lo];
    if (lo == hi) return a;
    std::nth_element(values.begin() + lo + 1, values.begin() + hi, values.end());
    return a + (index - lo) * (values[hi] - a);
}
struct Grid {
    int nx, ny;
    std::array<double, 6> transform{};
    std::string projection;
    size_t size() const { return static_cast<size_t>(nx) * ny; }
};
Grid grid(GDALDataset* ds) {
    Grid g{ds->GetRasterXSize(), ds->GetRasterYSize(), {}, ds->GetProjectionRef()};
    require(ds->GetGeoTransform(g.transform.data()) == CE_None, "Missing geotransform");
    return g;
}
void same_grid(const Grid& a, const Grid& b) {
    require(a.nx == b.nx && a.ny == b.ny, "Raster dimensions differ");
    for (int i = 0; i < 6; ++i)
        require(std::abs(a.transform[i] - b.transform[i]) < 1e-8, "Raster grids differ");
    OGRSpatialReference sa(a.projection.c_str()), sb(b.projection.c_str());
    require(sa.IsSame(&sb), "Raster coordinate systems differ");
}
std::vector<double> read_band(GDALDataset* ds, int band_number, const Grid& g) {
    require(band_number >= 1 && band_number <= ds->GetRasterCount(), "Band outside stack");
    auto* band = ds->GetRasterBand(band_number);
    std::vector<double> data(g.size());
    require(band->RasterIO(GF_Read, 0, 0, g.nx, g.ny, data.data(), g.nx, g.ny,
                          GDT_Float64, 0, 0) == CE_None, "Raster read failed");
    int defined = 0;
    const double nodata = band->GetNoDataValue(&defined);
    std::vector<uint8_t> mask;
    if (!(band->GetMaskFlags() & GMF_ALL_VALID)) {
        mask.resize(g.size());
        require(band->GetMaskBand()->RasterIO(GF_Read, 0, 0, g.nx, g.ny,
                mask.data(), g.nx, g.ny, GDT_Byte, 0, 0) == CE_None, "Validity read failed");
    }
    for (size_t i = 0; i < data.size(); ++i)
        if (!std::isfinite(data[i]) || (defined && data[i] == nodata) ||
            (!mask.empty() && !mask[i])) data[i] = NaN;
    return data;
}
std::vector<double> read_stack(GDALDataset* ds, std::vector<int> bands, const Grid& g) {
    // The deposited TIFFs interleave 32 years per compressed tile. Reading the
    // selected years together avoids repeatedly decompressing the same tile.
    for (int b : bands) require(b >= 1 && b <= ds->GetRasterCount(), "Band outside stack");
    std::vector<double> data(g.size() * bands.size());
    require(ds->RasterIO(GF_Read, 0, 0, g.nx, g.ny, data.data(), g.nx, g.ny,
            GDT_Float64, static_cast<int>(bands.size()), bands.data(), sizeof(double),
            sizeof(double) * g.nx, sizeof(double) * g.size()) == CE_None, "Stack read failed");
    for (size_t j = 0; j < bands.size(); ++j) {
        auto* band = ds->GetRasterBand(bands[j]);
        int defined = 0; const double nodata = band->GetNoDataValue(&defined);
        std::vector<uint8_t> mask;
        if (!(band->GetMaskFlags() & GMF_ALL_VALID)) {
            mask.resize(g.size());
            require(band->GetMaskBand()->RasterIO(GF_Read, 0, 0, g.nx, g.ny,
                    mask.data(), g.nx, g.ny, GDT_Byte, 0, 0) == CE_None, "Validity read failed");
        }
        for (size_t i = 0; i < g.size(); ++i) {
            double& value = data[j * g.size() + i];
            if (!std::isfinite(value) || (defined && value == nodata) ||
                (!mask.empty() && !mask[i])) value = NaN;
        }
    }
    return data;
}
std::vector<uint8_t> read_mask(const std::string& path, const Grid& g) {
    if (path == "NONE") return {};
    auto ds = open(path);
    same_grid(g, grid(ds.get()));
    auto values = read_band(ds.get(), 1, g);
    std::vector<uint8_t> mask(g.size());
    for (size_t i = 0; i < g.size(); ++i) {
        require(!std::isfinite(values[i]) || values[i] == 0 || values[i] == 1,
                "Mask must be binary");
        mask[i] = std::isfinite(values[i]) && values[i] == 1;
    }
    require(std::count(mask.begin(), mask.end(), 1) > 0, "Empty supplied mask");
    return mask;
}
Dataset create(const fs::path& path, const Grid& g, int bands, GDALDataType type) {
    char** options = nullptr;
    options = CSLSetNameValue(options, "COMPRESS", "DEFLATE");
    options = CSLSetNameValue(options, "TILED", "YES");
    options = CSLSetNameValue(options, "INTERLEAVE", "BAND");
    options = CSLSetNameValue(options, "BIGTIFF", "IF_SAFER");
    auto* ds = GetGDALDriverManager()->GetDriverByName("GTiff")->Create(
        path.c_str(), g.nx, g.ny, bands, type, options);
    CSLDestroy(options);
    require(ds != nullptr, "Cannot create " + path.string());
    ds->SetGeoTransform(const_cast<double*>(g.transform.data()));
    ds->SetProjection(g.projection.c_str());
    return Dataset(ds, [](GDALDataset* p) { GDALClose(p); });
}
template<class T> void write_band(GDALDataset* ds, int index, const Grid& g,
                                  std::vector<T>& values, GDALDataType type) {
    require(ds->GetRasterBand(index)->RasterIO(GF_Write, 0, 0, g.nx, g.ny,
            values.data(), g.nx, g.ny, type, 0, 0) == CE_None, "Raster write failed");
}
struct Layer { int band; std::string year, role; };
double number(const std::string& value) {
    if (value.empty() || value == "NA" || value == "nan") return NaN;
    return std::stod(value);
}
void summarize(const fs::path& input_path, const fs::path& output) {
    // Rows: site_id,signature,avulsion_pixels,parent_pixels,complete.
    // Input counts are generated from this program's raster outputs.
    std::ifstream input(input_path);
    require(input.good(), "Missing generated counts table");
    std::string line; std::getline(input, line);
    struct Total { uint64_t avulsion = 0, parent = 0; bool complete = true; int parts = 0; };
    std::map<std::string, std::map<std::string, Total>> sites;
    while (std::getline(input, line)) {
        auto f = split(line, ','); require(f.size() == 5, "Invalid counts row");
        auto& total = sites[f[0]][f[1]];
        total.avulsion += std::stoull(f[2]); total.parent += std::stoull(f[3]);
        total.complete = total.complete && f[4] == "1"; ++total.parts;
    }
    fs::create_directories(output);
    std::ofstream variants(output / "signature_ratios.csv");
    variants << "site_id,signature,avulsion_pixels,parent_pixels,style_ratio,complete,parts\n" << std::setprecision(17);
    std::ofstream chosen(output / "style_ratios.csv");
    chosen << "site_id,signature,avulsion_pixels,parent_pixels,style_ratio,signatures_available\n" << std::setprecision(17);
    for (const auto& entry : sites) {
        const Total* best = nullptr; std::string selected; int available = 0;
        for (const auto& variant : entry.second) {
            const auto& t = variant.second;
            const bool usable = t.complete && t.parent > 0;
            double ratio = usable ? static_cast<double>(t.avulsion) / t.parent : NaN;
            variants << entry.first << ',' << variant.first << ',' << t.avulsion << ',' << t.parent << ','
                     << ratio << ',' << t.complete << ',' << t.parts << '\n';
            if (usable) {
                ++available;
                if (!best || t.avulsion < best->avulsion) { best = &t; selected = variant.first; }
            }
        }
        if (best) chosen << entry.first << ',' << selected << ',' << best->avulsion << ',' << best->parent << ','
                         << static_cast<double>(best->avulsion) / best->parent << ',' << available << '\n';
        else chosen << entry.first << ",NA,0,0,nan,0\n";
    }
}
void statistics(const fs::path& input_path, const fs::path& output) {
    // Complete independent records only; no imputation of missing geometry.
    // Columns: site_id,style_ratio,width_m,distance_m,slope,morphology
    std::ifstream input(input_path); require(input.good(), "Missing geometry join");
    std::string line; std::getline(input, line);
    fs::create_directories(output);
    std::ofstream pairs(output / "statistical_points.csv");
    pairs << "site_id,style_ratio,normalized_distance,slope,morphology\n" << std::setprecision(17);
    std::map<int, std::array<std::vector<double>, 3>> groups;
    std::vector<double> x, y;
    while (std::getline(input, line)) {
        // A sentinel in the final column keeps empty trailing CSV fields explicit.
        auto f = split(line, ','); require(f.size() == 6, "Invalid geometry join row");
        double sr = number(f[1]), width = number(f[2]), distance = number(f[3]), slope = number(f[4]);
        int morphology = f[5] == "NA" ? 0 : std::stoi(f[5]);
        double normalized = std::isfinite(distance) && width > 0 ? distance / width : NaN;
        pairs << f[0] << ',' << sr << ',' << normalized << ',' << slope << ',' << morphology << '\n';
        if (normalized > 60 && sr > 0) { x.push_back(std::log10(normalized)); y.push_back(std::log10(sr)); }
        if (morphology >= 1 && morphology <= 3) {
            if (std::isfinite(sr)) groups[morphology][0].push_back(sr);
            if (std::isfinite(slope)) groups[morphology][1].push_back(slope);
            if (std::isfinite(normalized)) groups[morphology][2].push_back(normalized);
        }
    }
    std::ofstream summaries(output / "group_summaries.csv");
    summaries << "morphology,quantity,n,min,q25,median,q75,max\n" << std::setprecision(17);
    for (int group = 1; group <= 3; ++group)
        for (int quantity = 0; quantity < 3; ++quantity) {
            const auto& values = groups[group][quantity];
            summaries << group << ',' << std::array<std::string,3>{"style_ratio","slope","normalized_distance"}[quantity]
                      << ',' << values.size();
            for (double p : {0., .25, .5, .75, 1.}) summaries << ',' << quantile(values, p);
            summaries << '\n';
        }
    double slope = NaN, intercept = NaN, r2 = NaN;
    if (x.size() >= 3) {
        double mx = 0, my = 0; for (size_t i = 0; i < x.size(); ++i) { mx += x[i]; my += y[i]; }
        mx /= x.size(); my /= y.size(); double xx = 0, yy = 0, xy = 0;
        for (size_t i = 0; i < x.size(); ++i) { xx += (x[i]-mx)*(x[i]-mx); yy += (y[i]-my)*(y[i]-my); xy += (x[i]-mx)*(y[i]-my); }
        if (xx > 0) { slope = xy / xx; intercept = my - slope * mx; }
        if (xx > 0 && yy > 0) r2 = xy * xy / (xx * yy);
    }
    std::ofstream fit(output / "regression.csv");
    fit << "n,log10_intercept,log10_slope,r_squared\n" << std::setprecision(17)
        << x.size() << ',' << intercept << ',' << slope << ',' << r2 << '\n';
}
void run(const fs::path& manifest, const fs::path& output) {
    std::ifstream input(manifest);
    require(input.good(), "Cannot read manifest");
    std::map<std::string, std::string> config;
    std::string line;
    while (std::getline(input, line)) {
        auto fields = split(line, '\t');
        if (fields.size() == 2) config[fields[0]] = fields[1];
    }
    auto b = open(config.at("B")), g = open(config.at("G")), w = open(config.at("W"));
    Grid geo = grid(b.get());
    same_grid(geo, grid(g.get())); same_grid(geo, grid(w.get()));
    std::array<std::vector<uint8_t>, 4> masks;
    const std::array<std::string, 4> names{"avulsion_B", "parent_B", "avulsion_W", "parent_W"};
    for (size_t k = 0; k < 4; ++k) masks[k] = read_mask(config.at(names[k]), geo);
    std::ifstream layer_file(config.at("layers"));
    require(layer_file.good(), "Cannot read layers CSV");
    std::getline(layer_file, line);
    std::vector<Layer> layers;
    while (std::getline(layer_file, line)) {
        auto f = split(line, ',');
        require(f.size() == 3 && (f[2] == "A" || f[2] == "P"), "Invalid layer record");
        layers.push_back({std::stoi(f[0]), f[1], f[2]});
    }
    require(!layers.empty() && layers.size() < 65535, "Invalid layer count");
    std::vector<int> selected_bands;
    for (const auto& layer : layers) selected_bands.push_back(layer.band);
    auto all_b = read_stack(b.get(), selected_bands, geo);
    auto all_g = read_stack(g.get(), selected_bands, geo);
    auto all_w = read_stack(w.get(), selected_bands, geo);
    fs::create_directories(output);
    // Prevent a mask removed from a later configuration leaving a stale result.
    for (const auto& name : names) {
        fs::remove(output / (name + ".tif"));
        fs::remove(output / (name + "_valid.tif"));
    }
    auto annual_b = create(output / "annual_B.tif", geo, layers.size(), GDT_Byte);
    auto annual_w = create(output / "annual_W.tif", geo, layers.size(), GDT_Byte);
    std::array<std::vector<uint16_t>, 4> counts, valid;
    for (size_t k = 0; k < 4; ++k) {
        counts[k].resize(geo.size()); valid[k].resize(geo.size());
    }
    std::ofstream annual(output / "annual.csv");
    annual << "band,year,role,valid_pixels,B90,G50,W75,bright_pixels,wet_pixels\n" << std::setprecision(17);
    size_t index = 0;
    for (const auto& layer : layers) {
        const size_t start = index * geo.size(), end = start + geo.size();
        std::vector<double> bv(all_b.begin() + start, all_b.begin() + end);
        std::vector<double> gv(all_g.begin() + start, all_g.begin() + end);
        std::vector<double> wv(all_w.begin() + start, all_w.begin() + end);
        size_t nvalid = 0;
        for (size_t i = 0; i < geo.size(); ++i) {
            if (std::isfinite(bv[i]) && std::isfinite(gv[i]) && std::isfinite(wv[i])) ++nvalid;
            else bv[i] = gv[i] = wv[i] = NaN;
        }
        const double qb = quantile(bv, .9), qg = quantile(gv, .5), qw = quantile(wv, .75);
        std::vector<uint8_t> bright(geo.size(), 255), wet(geo.size(), 255);
        size_t nb = 0, nw = 0;
        for (size_t i = 0; i < geo.size(); ++i) {
            if (!std::isfinite(bv[i])) continue;
            bright[i] = bv[i] > qb && gv[i] < qg;
            wet[i] = wv[i] > qw && gv[i] < qg;
            nb += bright[i]; nw += wet[i];
            const size_t role = layer.role == "A" ? 0 : 1;
            for (size_t k : {role, role + 2}) {
                if (!masks[k].empty() && masks[k][i]) {
                    ++valid[k][i]; counts[k][i] += (k < 2 ? bright[i] : wet[i]);
                }
            }
        }
        ++index;
        for (auto* ds : {annual_b.get(), annual_w.get()}) {
            auto* band = ds->GetRasterBand(index);
            band->SetNoDataValue(255);
            band->SetDescription((layer.year + ":" + layer.role).c_str());
            band->SetMetadataItem("SOURCE_BAND", std::to_string(layer.band).c_str());
        }
        write_band(annual_b.get(), index, geo, bright, GDT_Byte);
        write_band(annual_w.get(), index, geo, wet, GDT_Byte);
        annual << layer.band << ',' << layer.year << ',' << layer.role << ',' << nvalid << ','
               << qb << ',' << qg << ',' << qw << ',' << nb << ',' << nw << '\n';
        std::cout << output.filename().string() << " band " << layer.band << " " << layer.year
                  << " valid=" << nvalid << std::endl;
    }
    std::ofstream areas(output / "areas.csv");
    areas << "role,signature,mask_pixels,observed_mask_pixels,fingerprint_pixels,pixel_area_native\n"
          << std::setprecision(17);
    double area = std::abs(geo.transform[1] * geo.transform[5] - geo.transform[2] * geo.transform[4]);
    for (size_t k = 0; k < 4; ++k) {
        if (masks[k].empty()) continue;
        size_t support = 0, observed = 0, detected = 0;
        for (size_t i = 0; i < geo.size(); ++i) {
            support += masks[k][i]; observed += valid[k][i] > 0; detected += counts[k][i] > 0;
            require(counts[k][i] <= valid[k][i], "Fingerprint exceeds observed years");
        }
        auto fp = create(output / (names[k] + ".tif"), geo, 1, GDT_UInt16);
        write_band(fp.get(), 1, geo, counts[k], GDT_UInt16);
        auto vp = create(output / (names[k] + "_valid.tif"), geo, 1, GDT_UInt16);
        write_band(vp.get(), 1, geo, valid[k], GDT_UInt16);
        areas << (k % 2 ? "parent" : "avulsion") << ',' << (k < 2 ? "B" : "W") << ','
              << support << ',' << observed << ',' << detected << ',' << area << '\n';
    }
}
void selftest() {
    size_t checks = 0;
    auto test = [&](bool condition, const std::string& name) { require(condition, name); ++checks; };
    test(std::isnan(quantile({}, .5)), "Empty sample is undefined");
    test(quantile({4}, .9) == 4, "Singleton");
    test(quantile({0, 10}, .9) == 9, "Linear interpolation");
    test(quantile({NaN, 1, 2, 3}, .5) == 2, "Missing-value exclusion");
    test(quantile({3, 3, 3}, .9) == 3, "Tied values");
    for (int n = 2; n < 64; ++n) {
        std::vector<double> x;
        for (int i = n - 1; i >= 0; --i) x.push_back(2. * i - 10.);
        for (double p : {0., .1, .5, .75, .9, 1.})
            test(std::abs(quantile(x, p) - (2 * (n - 1) * p - 10)) < 1e-12, "Analytical quantile");
    }
    test(!(3. > quantile({3, 3, 3}, .9)), "Strict threshold rejects constant field");
    std::cout << "Passed " << checks << " analytical limiting-case checks\n";
}
int main(int argc, char** argv) {
    try {
        GDALAllRegister();
        GDALSetCacheMax64(256LL * 1024 * 1024);
        if (argc == 2 && std::string(argv[1]) == "selftest") selftest();
        else if (argc == 3) run(argv[1], argv[2]);
        else if (argc == 4 && std::string(argv[1]) == "summarize") summarize(argv[2], argv[3]);
        else if (argc == 4 && std::string(argv[1]) == "statistics") statistics(argv[2], argv[3]);
        else throw std::runtime_error("Usage: fingerprint selftest | MANIFEST.tsv OUTPUT_DIR | summarize COUNTS.csv OUTPUT_DIR | statistics RECORDS.csv OUTPUT_DIR");
        return 0;
    } catch (const std::exception& e) {
        std::cerr << "ERROR: " << e.what() << '\n'; return 1;
    }
}
