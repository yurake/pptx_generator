using System.Text.Json;
using DocumentFormat.OpenXml.Packaging;
using DocumentFormat.OpenXml.Presentation;
using A = DocumentFormat.OpenXml.Drawing;

namespace Polisher.Tests;

internal static class Program
{
    private static int Main(string[] args)
    {
        try
        {
            RunAllTests();
            Console.WriteLine("All Polisher tests passed.");
            return 0;
        }
        catch (Exception ex)
        {
            Console.Error.WriteLine(ex.ToString());
            return 1;
        }
    }

    private static void RunAllTests()
    {
        TestDryRunProducesSummary();
        TestApplyPolishAdjustsFontSize();
    }

    private static void TestDryRunProducesSummary()
    {
        using var temp = new TempDirectory();
        var pptxPath = CopySamplePresentation(temp, "dryrun-input.pptx");
        var rulesPath = WriteRules(temp, """{"min_font_size_pt":18}""");

        using var stdout = new StringWriter();
        using var stderr = new StringWriter();
        var exitCode = Polisher.Program.Execute(
            new[] { "--input", pptxPath, "--rules", rulesPath, "--dry-run" },
            stdout,
            stderr
        );

        AssertEqual(0, exitCode, "Dry-run exit code");
        AssertTrue(string.IsNullOrWhiteSpace(stderr.ToString()), "Dry-run stderr should be empty");

        using var document = JsonDocument.Parse(stdout.ToString());
        var root = document.RootElement;
        AssertTrue(root.GetProperty("Slides").GetInt32() > 0, "Summary must report slide count");
    }

    private static void TestApplyPolishAdjustsFontSize()
    {
        using var temp = new TempDirectory();
        var pptxPath = CopySamplePresentation(temp, "apply-input.pptx");
        var rulesPath = WriteRules(temp, """{"min_font_size_pt":18,"default_font_color":"#000000"}""");

        // Prepare slide with small font to trigger adjustment
        using (var doc = PresentationDocument.Open(pptxPath, true))
        {
            var slidePart = doc.PresentationPart?.SlideParts.First()
                ?? throw new InvalidOperationException("Slide not found");
            var run = slidePart.Slide.Descendants<A.Run>().FirstOrDefault()
                ?? throw new InvalidOperationException("Text run not found");
            var props = run.RunProperties ??= new A.RunProperties();
            props.FontSize = 1200; // 12pt
            props.RemoveAllChildren<A.SolidFill>();
            slidePart.Slide.Save();
        }

        using var stdout = new StringWriter();
        using var stderr = new StringWriter();
        var exitCode = Polisher.Program.Execute(
            new[] { "--input", pptxPath, "--rules", rulesPath },
            stdout,
            stderr
        );

        AssertEqual(0, exitCode, "Apply exit code");
        AssertTrue(string.IsNullOrWhiteSpace(stderr.ToString()), "Apply stderr should be empty");

        using var summaryDoc = JsonDocument.Parse(stdout.ToString());
        var summary = summaryDoc.RootElement;
        AssertTrue(summary.GetProperty("AdjustedFontSize").GetInt32() > 0, "Font adjustments must be reported");

        using (var doc = PresentationDocument.Open(pptxPath, false))
        {
            var slidePart = doc.PresentationPart?.SlideParts.First()
                ?? throw new InvalidOperationException("Slide not found");
            var run = slidePart.Slide.Descendants<A.Run>().FirstOrDefault()
                ?? throw new InvalidOperationException("Text run not found");
            var fontSize = run.RunProperties?.FontSize?.Value ?? 0;
            AssertTrue(fontSize >= 1800, "Font size should be raised to at least 18pt");
        }
    }

    private static string CopySamplePresentation(TempDirectory temp, string targetName)
    {
        var repoRoot = FindRepositoryRoot();
        var samplePath = Path.Combine(repoRoot, "dotnet", "Polisher.Tests", "TestData", "sample_output.pptx");
        if (!File.Exists(samplePath))
        {
            throw new FileNotFoundException("Sample template not found", samplePath);
        }

        var destination = Path.Combine(temp.Path, targetName);
        File.Copy(samplePath, destination, overwrite: true);
        return destination;
    }

    private static string WriteRules(TempDirectory temp, string json)
    {
        var path = Path.Combine(temp.Path, "rules.json");
        File.WriteAllText(path, json);
        return path;
    }

    private static string FindRepositoryRoot()
    {
        var dir = new DirectoryInfo(AppContext.BaseDirectory);
        while (dir != null)
        {
            if (File.Exists(Path.Combine(dir.FullName, "pyproject.toml")))
            {
                return dir.FullName;
            }
            dir = dir.Parent;
        }

        throw new InvalidOperationException("Failed to locate repository root.");
    }

    private static void AssertTrue(bool condition, string message)
    {
        if (!condition)
        {
            throw new InvalidOperationException(message);
        }
    }

    private static void AssertEqual<T>(T expected, T actual, string message)
    {
        if (!EqualityComparer<T>.Default.Equals(expected, actual))
        {
            throw new InvalidOperationException($"{message}: expected {expected}, actual {actual}");
        }
    }

    private sealed class TempDirectory : IDisposable
    {
        public string Path { get; }

        public TempDirectory()
        {
            Path = System.IO.Path.Combine(System.IO.Path.GetTempPath(), $"polisher-tests-{Guid.NewGuid():N}");
            Directory.CreateDirectory(Path);
        }

        public void Dispose()
        {
            try
            {
                if (Directory.Exists(Path))
                {
                    Directory.Delete(Path, recursive: true);
                }
            }
            catch
            {
                // ignore cleanup errors
            }
        }
    }
}
