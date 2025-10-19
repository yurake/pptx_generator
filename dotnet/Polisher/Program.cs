using System.Text.Json;
using DocumentFormat.OpenXml;
using DocumentFormat.OpenXml.Drawing;
using DocumentFormat.OpenXml.Packaging;
using DocumentFormat.OpenXml.Presentation;
using A = DocumentFormat.OpenXml.Drawing;

namespace Polisher;

internal static class Program
{
    private sealed record Options(string InputPath, string? RulesPath, bool DryRun);

    private sealed record PolisherConfig(
        double MinFontSizePt,
        string? DefaultFontColor,
        string? DefaultFontName,
        bool NormalizeParagraphSpacing
    )
    {
        public static PolisherConfig Default { get; } = new(18.0, "#333333", null, false);

        public static PolisherConfig Load(string? path)
        {
            if (string.IsNullOrWhiteSpace(path))
            {
                return Default;
            }

            if (!File.Exists(path))
            {
                throw new FileNotFoundException($"Rules file not found: {path}");
            }

            using var stream = File.OpenRead(path);
            var payload = JsonSerializer.Deserialize<Dictionary<string, JsonElement>>(stream);
            if (payload is null)
            {
                return Default;
            }

            double minFont = Default.MinFontSizePt;
            string? defaultColor = Default.DefaultFontColor;
            string? defaultFont = Default.DefaultFontName;
            bool normalizeSpacing = Default.NormalizeParagraphSpacing;

            if (payload.TryGetValue("min_font_size_pt", out var minFontElement) &&
                minFontElement.TryGetDouble(out var minFontValue) &&
                minFontValue > 0)
            {
                minFont = minFontValue;
            }

            if (payload.TryGetValue("default_font_color", out var colorElement) &&
                colorElement.ValueKind == JsonValueKind.String)
            {
                defaultColor = NormalizeHex(colorElement.GetString());
            }

            if (payload.TryGetValue("default_font_name", out var fontElement) &&
                fontElement.ValueKind == JsonValueKind.String)
            {
                var fontName = fontElement.GetString();
                if (!string.IsNullOrWhiteSpace(fontName))
                {
                    defaultFont = fontName;
                }
            }

            if (payload.TryGetValue("normalize_paragraph_spacing", out var spacingElement))
            {
                if (spacingElement.ValueKind == JsonValueKind.True ||
                    spacingElement.ValueKind == JsonValueKind.False)
                {
                    normalizeSpacing = spacingElement.GetBoolean();
                }
            }

            return new PolisherConfig(minFont, defaultColor, defaultFont, normalizeSpacing);
        }

        private static string? NormalizeHex(string? value)
        {
            if (string.IsNullOrWhiteSpace(value))
            {
                return null;
            }

            value = value.Trim();
            return value.StartsWith("#", StringComparison.Ordinal) ? value : $"#{value}";
        }
    }

    private sealed class Summary
    {
        public int Slides { get; set; }
        public int AdjustedFontSize { get; set; }
        public int AdjustedColor { get; set; }
    }

    public static int Main(string[] args) => Execute(args);

    internal static int Execute(string[] args, TextWriter? stdout = null, TextWriter? stderr = null)
    {
        stdout ??= Console.Out;
        stderr ??= Console.Error;

        try
        {
            var options = ParseOptions(args);
            var config = PolisherConfig.Load(options.RulesPath);
            var summary = options.DryRun
                ? AnalyzeOnly(options.InputPath, config)
                : ApplyPolish(options.InputPath, config);

            stdout.WriteLine(
                JsonSerializer.Serialize(
                    summary,
                    new JsonSerializerOptions { WriteIndented = true }
                )
            );

            return 0;
        }
        catch (Exception ex)
        {
            stderr.WriteLine(ex.Message);
            return 1;
        }
    }

    private static Summary ApplyPolish(string pptxPath, PolisherConfig config)
    {
        using var document = PresentationDocument.Open(pptxPath, true);
        var presentationPart = document.PresentationPart
            ?? throw new InvalidDataException("Presentation part not found.");

        var summary = new Summary();

        foreach (var slidePart in EnumerateSlides(presentationPart))
        {
            summary.Slides += 1;
            summary.AdjustedFontSize += ApplyFontSizeRules(slidePart, config);
            summary.AdjustedColor += ApplyColorRules(slidePart, config);
        }

        presentationPart.Presentation?.Save();
        return summary;
    }

    private static Summary AnalyzeOnly(string pptxPath, PolisherConfig config)
    {
        using var document = PresentationDocument.Open(pptxPath, false);
        var presentationPart = document.PresentationPart
            ?? throw new InvalidDataException("Presentation part not found.");

        var summary = new Summary();
        foreach (var slidePart in EnumerateSlides(presentationPart))
        {
            summary.Slides += 1;
            summary.AdjustedFontSize += CountFontSizeAdjustments(slidePart, config);
            summary.AdjustedColor += CountColorAdjustments(slidePart, config);
        }

        return summary;
    }

    private static Options ParseOptions(string[] args)
    {
        string? inputPath = null;
        string? rulesPath = null;
        bool dryRun = false;

        for (int index = 0; index < args.Length; index += 1)
        {
            var token = args[index];
            if (!token.StartsWith("--", StringComparison.Ordinal))
            {
                continue;
            }

            switch (token)
            {
                case "--input":
                    inputPath = RequireValue(args, ref index, token);
                    break;
                case "--rules":
                    rulesPath = RequireValue(args, ref index, token);
                    break;
                case "--dry-run":
                    dryRun = true;
                    break;
                default:
                    throw new ArgumentException($"Unknown option: {token}");
            }
        }

        if (string.IsNullOrWhiteSpace(inputPath))
        {
            throw new ArgumentException("--input is required");
        }

        return new Options(System.IO.Path.GetFullPath(inputPath), rulesPath, dryRun);
    }

    private static string RequireValue(string[] args, ref int index, string token)
    {
        if (index + 1 >= args.Length || args[index + 1].StartsWith("--", StringComparison.Ordinal))
        {
            throw new ArgumentException($"{token} requires a value");
        }

        index += 1;
        return args[index];
    }

    private static int ApplyFontSizeRules(SlidePart slidePart, PolisherConfig config)
    {
        var threshold = (int)Math.Round(config.MinFontSizePt * 100, MidpointRounding.AwayFromZero);
        int adjustments = 0;

        foreach (var run in slidePart.Slide.Descendants<A.Run>())
        {
            var properties = run.RunProperties ??= new A.RunProperties();
            var current = properties.FontSize?.Value ?? 0;
            if (current >= threshold)
            {
                continue;
            }

            properties.FontSize = threshold;
            adjustments += 1;

            if (!string.IsNullOrWhiteSpace(config.DefaultFontName))
            {
                properties.RemoveAllChildren<A.LatinFont>();
                properties.AppendChild(new A.LatinFont { Typeface = config.DefaultFontName });
            }
        }

        slidePart.Slide.Save();
        return adjustments;
    }

    private static int CountFontSizeAdjustments(SlidePart slidePart, PolisherConfig config)
    {
        var threshold = (int)Math.Round(config.MinFontSizePt * 100, MidpointRounding.AwayFromZero);
        int adjustments = 0;

        foreach (var run in slidePart.Slide.Descendants<A.Run>())
        {
            var current = run.RunProperties?.FontSize?.Value ?? 0;
            if (current < threshold)
            {
                adjustments += 1;
            }
        }

        return adjustments;
    }

    private static int ApplyColorRules(SlidePart slidePart, PolisherConfig config)
    {
        if (string.IsNullOrWhiteSpace(config.DefaultFontColor))
        {
            return 0;
        }

        int adjustments = 0;
        var targetColorHex = config.DefaultFontColor.TrimStart('#');

        foreach (var run in slidePart.Slide.Descendants<A.Run>())
        {
            var properties = run.RunProperties ??= new A.RunProperties();
            var solidFill = properties.GetFirstChild<A.SolidFill>();
            var hex = ExtractHexColor(solidFill);
            if (!string.Equals(hex, targetColorHex, StringComparison.OrdinalIgnoreCase))
            {
                properties.RemoveAllChildren<A.SolidFill>();
                properties.AppendChild(CreateSolidFill(targetColorHex));
                adjustments += 1;
            }
        }

        slidePart.Slide.Save();
        return adjustments;
    }

    private static int CountColorAdjustments(SlidePart slidePart, PolisherConfig config)
    {
        if (string.IsNullOrWhiteSpace(config.DefaultFontColor))
        {
            return 0;
        }

        int adjustments = 0;
        var targetColorHex = config.DefaultFontColor.TrimStart('#');

        foreach (var run in slidePart.Slide.Descendants<A.Run>())
        {
            var hex = ExtractHexColor(run.RunProperties?.GetFirstChild<A.SolidFill>());
            if (!string.Equals(hex, targetColorHex, StringComparison.OrdinalIgnoreCase))
            {
                adjustments += 1;
            }
        }

        return adjustments;
    }

    private static string? ExtractHexColor(A.SolidFill? fill)
    {
        var rgb = fill?.RgbColorModelHex;
        return rgb?.Val?.Value;
    }

    private static A.SolidFill CreateSolidFill(string hex)
    {
        return new A.SolidFill
        {
            RgbColorModelHex = new A.RgbColorModelHex { Val = hex },
        };
    }

    private static IEnumerable<SlidePart> EnumerateSlides(PresentationPart presentationPart)
    {
        var slideIdList = presentationPart.Presentation?.SlideIdList;
        if (slideIdList is null)
        {
            yield break;
        }

        foreach (var slideId in slideIdList.Elements<SlideId>())
        {
            if (slideId.RelationshipId is null)
            {
                continue;
            }

            if (presentationPart.GetPartById(slideId.RelationshipId) is SlidePart part)
            {
                yield return part;
            }
        }
    }
}
