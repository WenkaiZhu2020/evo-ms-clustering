package org.evomicro.sootextractor;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertArrayEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertTrue;

import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.List;
import java.util.Map;
import javax.tools.JavaCompiler;
import javax.tools.ToolProvider;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;

final class SootExtractorCliTest {
  @TempDir Path tempDir;

  @Test
  void extractsClassNodesTypeDependenciesAndCallDependencies() throws IOException {
    Path classesDir = compileFixture();

    Path outDir = tempDir.resolve("out");
    int exitCode =
        SootExtractorCli.run(
            new String[] {
              "--subject",
              "jpetstore",
              "--classes-dir",
              classesDir.toString(),
              "--classpath",
              classesDir.toString(),
              "--app-packages",
              "com.example",
              "--out-dir",
              outDir.toString()
            });

    assertEquals(0, exitCode);
    List<String> classNodes = Files.readAllLines(outDir.resolve("class_nodes.csv"));
    assertEquals(String.join(",", SootExtractorCli.CLASS_NODES_COLUMNS), classNodes.get(0));
    assertTrue(classNodes.stream().anyMatch(line -> line.contains("com.example.A,com.example.A,com.example")));
    assertTrue(classNodes.stream().anyMatch(line -> line.contains("com.example.B,com.example.B,com.example")));

    List<String> dependencies = Files.readAllLines(outDir.resolve("structural_dependencies.csv"));
    assertEquals(String.join(",", SootExtractorCli.STRUCTURAL_DEPENDENCY_COLUMNS), dependencies.get(0));
    assertTrue(
        dependencies.stream()
            .anyMatch(line -> line.contains("com.example.A,com.example.Base,type,1,extends_type_reference")));
    assertTrue(
        dependencies.stream()
            .anyMatch(line -> line.contains("com.example.A,com.example.I,type,1,implements_type_reference")));
    assertTrue(
        dependencies.stream()
            .anyMatch(line -> line.contains("com.example.A,com.example.B,type,1,field_type_reference")));
    assertTrue(
        dependencies.stream()
            .anyMatch(line -> line.contains("com.example.A,com.example.B,type,1,method_parameter_type_reference")));
    assertTrue(
        dependencies.stream()
            .anyMatch(line -> line.contains("com.example.A,com.example.B,type,1,method_return_type_reference")));
    assertTrue(dependencies.stream().anyMatch(line -> line.contains("com.example.A,com.example.B,call,2,method_call")));

    List<String> ssaFlows = Files.readAllLines(outDir.resolve("ssa_flow_edges.csv"));
    assertEquals(String.join(",", SootExtractorCli.SSA_FLOW_COLUMNS), ssaFlows.get(0));
    assertTrue(
        ssaFlows.stream().anyMatch(line -> line.contains("com.example.B,com.example.C,return_value_flow,3")));
    assertTrue(
        ssaFlows.stream().anyMatch(line -> line.contains("com.example.B,com.example.C,argument_passing_flow,3")));
    assertTrue(Files.notExists(outDir.resolve("method_bodies.csv")));
  }

  @Test
  void writesMethodBodiesOnlyToExplicitIsolatedPath() throws IOException {
    Path classesDir = compileFixture();
    Path outDir = tempDir.resolve("out");
    Path methodBodyOut = tempDir.resolve("stage3b/method_bodies.csv");
    int exitCode =
        SootExtractorCli.run(
            new String[] {
              "--subject",
              "fixture",
              "--classes-dir",
              classesDir.toString(),
              "--classpath",
              classesDir.toString(),
              "--app-packages",
              "com.example",
              "--out-dir",
              outDir.toString(),
              "--method-body-out",
              methodBodyOut.toString()
            });

    assertEquals(0, exitCode);
    assertTrue(Files.exists(methodBodyOut));
    List<String> rows = Files.readAllLines(methodBodyOut);
    assertEquals(String.join(",", SootExtractorCli.METHOD_BODY_COLUMNS), rows.get(0));
    assertTrue(rows.size() > 1);
    assertTrue(Files.notExists(outDir.resolve("method_bodies.csv")));
  }

  @Test
  void rejectsMissingClassesDirectory() {
    Path outDir = tempDir.resolve("out");
    int exitCode =
        SootExtractorCli.run(
            new String[] {
              "--subject",
              "jpetstore",
              "--classes-dir",
              tempDir.resolve("missing").toString(),
              "--classpath",
              tempDir.resolve("missing").toString(),
              "--app-packages",
              "org.mybatis.jpetstore",
              "--out-dir",
              outDir.toString()
            });

    assertEquals(2, exitCode);
    assertTrue(Files.notExists(outDir));
  }

  @Test
  void excludesApplicationClassesByPackagePrefix() throws IOException {
    Path classesDir = compileFixture();

    Path outDir = tempDir.resolve("filtered-out");
    int exitCode =
        SootExtractorCli.run(
            new String[] {
              "--subject",
              "fixture",
              "--classes-dir",
              classesDir.toString(),
              "--classpath",
              classesDir.toString(),
              "--app-packages",
              "com.example",
              "--exclude-packages",
              "com.example.noise",
              "--out-dir",
              outDir.toString()
            });

    assertEquals(0, exitCode);
    List<String> classNodes = Files.readAllLines(outDir.resolve("class_nodes.csv"));
    assertTrue(classNodes.stream().noneMatch(line -> line.contains("com.example.noise")));

    List<String> dependencies = Files.readAllLines(outDir.resolve("structural_dependencies.csv"));
    assertTrue(dependencies.stream().noneMatch(line -> line.contains("com.example.noise")));

    List<String> ssaFlows = Files.readAllLines(outDir.resolve("ssa_flow_edges.csv"));
    assertTrue(ssaFlows.stream().noneMatch(line -> line.contains("com.example.noise")));
  }

  @Test
  void rendersDeterministicClassDeclarationContract() throws IOException {
    Path classesDir = compileFixture();
    SootExtractorCli.ExtractionResult result = extractFixture(classesDir);

    Map<String, SootExtractorCli.ClassDeclaration> declarations =
        result.semanticInputs().stream().collect(java.util.stream.Collectors.toMap(
            SootExtractorCli.ClassDeclaration::classId, declaration -> declaration));

    SootExtractorCli.ClassDeclaration child = declarations.get("com.example.Child");
    assertEquals("class", child.kind());
    assertTrue(child.superclassPresent());
    assertEquals(
        "public class Child extends Parent {\n"
            + "    void alpha();\n"
            + "    int[] arrays(String[], int);\n"
            + "    void privateMethod();\n"
            + "    void zeta();\n"
            + "}\n",
        child.semanticText());
    assertFalse(child.semanticText().contains("public void"));
    assertFalse(child.semanticText().contains("static"));
    assertTrue(child.semanticText().endsWith("}\n"));
    assertEquals(64, child.inputHash().length());
    assertEquals(child.inputHash(), SootExtractorCli.classDeclaration(
        soot.Scene.v().getSootClass("com.example.Child")).inputHash());

    SootExtractorCli.ClassDeclaration annotated = declarations.get("com.example.Annotated");
    assertTrue(annotated.semanticText().startsWith("@Alpha\n@Beta\npublic class Annotated"));
    assertEquals(2, annotated.annotationCount());
    assertTrue(annotated.semanticText().contains("double calculate(int, String[]);"));

    assertEquals("interface", declarations.get("com.example.Marker").kind());
    assertEquals("enum", declarations.get("com.example.EnumKind").kind());
    assertEquals("abstract class", declarations.get("com.example.AbstractKind").kind());
    assertEquals("public interface Marker {\n}\n", declarations.get("com.example.Marker").semanticText());
    assertEquals(
        "public class Multi implements Aard, Zed {\n}\n",
        declarations.get("com.example.Multi").semanticText());
    assertEquals("class PackagePrivateKind {\n}\n", declarations.get("com.example.PackagePrivateKind").semanticText());
    assertTrue(declarations.get("com.example.GenericImpl").semanticText().contains("String convert(String);"));
    assertFalse(declarations.get("com.example.GenericImpl").semanticText().contains("Object convert(Object)"));
  }

  @Test
  void writesStableSemanticCsvRowsInClassIdOrder() throws IOException {
    Path classesDir = compileFixture();
    Path outDir = tempDir.resolve("semantic-out");
    Path semanticOut = tempDir.resolve("semantic-inputs/jpetstore_class_declarations.csv");
    int exitCode =
        SootExtractorCli.run(
            new String[] {
              "--subject", "jpetstore",
              "--classes-dir", classesDir.toString(),
              "--classpath", classesDir.toString(),
              "--app-packages", "com.example",
              "--out-dir", outDir.toString(),
              "--semantic-out", semanticOut.toString()
            });

    assertEquals(0, exitCode);
    byte[] firstBytes = Files.readAllBytes(semanticOut);
    String firstText = new String(firstBytes, StandardCharsets.UTF_8);
    assertTrue(firstText.startsWith(String.join(",", SootExtractorCli.SEMANTIC_INPUT_COLUMNS) + "\n"));
    assertTrue(firstText.indexOf("jpetstore,com.example.AbstractKind,") < firstText.indexOf("jpetstore,com.example.Child,"));

    assertEquals(0, SootExtractorCli.run(
        new String[] {
          "--subject", "jpetstore",
          "--classes-dir", classesDir.toString(),
          "--classpath", classesDir.toString(),
          "--app-packages", "com.example",
          "--out-dir", outDir.toString(),
          "--semantic-out", semanticOut.toString()
        }));
    assertArrayEquals(firstBytes, Files.readAllBytes(semanticOut));
  }

  @Test
  void exclusionPrefixesMustUseQualifiedPackageNames() {
    assertTrue(
        SootExtractorCli.isApplicationClass(
            "com.example.noise.Primitive", List.of("com.example"), List.of("noise")));
    assertFalse(
        SootExtractorCli.isApplicationClass(
            "com.example.noise.Primitive",
            List.of("com.example"),
            List.of("com.example.noise")));
  }

  private Path compileFixture() throws IOException {
    Path sourceRoot = tempDir.resolve("src");
    Path packageDir = sourceRoot.resolve("com/example");
    Files.createDirectories(packageDir);
    writeSource(packageDir.resolve("I.java"), "package com.example; public interface I {}");
    writeSource(packageDir.resolve("Marker.java"), "package com.example; public interface Marker {}");
    writeSource(packageDir.resolve("Aard.java"), "package com.example; public interface Aard {}");
    writeSource(packageDir.resolve("Zed.java"), "package com.example; public interface Zed {}");
    writeSource(packageDir.resolve("Multi.java"), "package com.example; public class Multi implements Zed, Aard {}");
    writeSource(packageDir.resolve("PackagePrivateKind.java"), "package com.example; class PackagePrivateKind {}");
    writeSource(packageDir.resolve("Generic.java"), "package com.example; public interface Generic<T> { T convert(T input); }");
    writeSource(
        packageDir.resolve("GenericImpl.java"),
        "package com.example; public class GenericImpl implements Generic<String> { public String convert(String input) { return input; } }");
    writeSource(packageDir.resolve("Base.java"), "package com.example; public class Base {}");
    writeSource(packageDir.resolve("Parent.java"), "package com.example; public class Parent { public void inherited() {} }");
    writeSource(
        packageDir.resolve("Child.java"),
        "package com.example; public class Child extends Parent { static { int x = 1; } public Child() {} public static final void zeta() {} private synchronized void privateMethod() {} void alpha() {} public int[] arrays(String[] names, int count) { return new int[count]; } }");
    writeSource(packageDir.resolve("AbstractKind.java"), "package com.example; public abstract class AbstractKind { public abstract void work(); }");
    writeSource(packageDir.resolve("EnumKind.java"), "package com.example; public enum EnumKind { ONE }");
    writeSource(packageDir.resolve("Alpha.java"), "package com.example; @java.lang.annotation.Retention(java.lang.annotation.RetentionPolicy.RUNTIME) public @interface Alpha {}");
    writeSource(packageDir.resolve("Beta.java"), "package com.example; @java.lang.annotation.Retention(java.lang.annotation.RetentionPolicy.RUNTIME) public @interface Beta {}");
    writeSource(
        packageDir.resolve("Annotated.java"),
        "package com.example; @Beta @Alpha public class Annotated { public double calculate(int count, String[] values) { return count; } }");
    writeSource(packageDir.resolve("B.java"), "package com.example; public class B { public B produce() { return this; } }");
    writeSource(packageDir.resolve("C.java"), "package com.example; public class C { public void consume(B value) {} }");
    Path noiseDir = packageDir.resolve("noise");
    Files.createDirectories(noiseDir);
    writeSource(noiseDir.resolve("Primitive.java"), "package com.example.noise; public class Primitive {}");
    writeSource(
        packageDir.resolve("A.java"),
        """
        package com.example;
        public class A extends Base implements I {
          private B field;
          public B link(B param) {
            C consumer = new C();
            B produced = param.produce();
            consumer.consume(produced);
            consumer.consume(param);
            return produced;
          }
        }
        """);

    Path classesDir = tempDir.resolve("classes");
    Files.createDirectories(classesDir);
    JavaCompiler compiler = ToolProvider.getSystemJavaCompiler();
    assertTrue(compiler != null, "tests require a JDK, not a JRE");
    int exitCode =
        compiler.run(
            null,
            null,
            null,
            "--release",
            "17",
            "-d",
            classesDir.toString(),
            packageDir.resolve("I.java").toString(),
            packageDir.resolve("Marker.java").toString(),
            packageDir.resolve("Aard.java").toString(),
            packageDir.resolve("Zed.java").toString(),
            packageDir.resolve("Multi.java").toString(),
            packageDir.resolve("PackagePrivateKind.java").toString(),
            packageDir.resolve("Generic.java").toString(),
            packageDir.resolve("GenericImpl.java").toString(),
            packageDir.resolve("Base.java").toString(),
            packageDir.resolve("Parent.java").toString(),
            packageDir.resolve("Child.java").toString(),
            packageDir.resolve("AbstractKind.java").toString(),
            packageDir.resolve("EnumKind.java").toString(),
            packageDir.resolve("Alpha.java").toString(),
            packageDir.resolve("Beta.java").toString(),
            packageDir.resolve("Annotated.java").toString(),
            packageDir.resolve("B.java").toString(),
            packageDir.resolve("C.java").toString(),
            noiseDir.resolve("Primitive.java").toString(),
            packageDir.resolve("A.java").toString());
    assertEquals(0, exitCode);
    return classesDir;
  }

  private SootExtractorCli.ExtractionResult extractFixture(Path classesDir) throws IOException {
    List<String> applicationClasses = SootExtractorCli.discoverApplicationClasses(classesDir, List.of("com.example"));
    return SootExtractorCli.extractStructuralDependencies(
        classesDir,
        classesDir.toString(),
        applicationClasses,
        new java.util.LinkedHashSet<>(applicationClasses));
  }

  private static void writeSource(Path path, String source) throws IOException {
    Files.writeString(path, source, StandardCharsets.UTF_8);
  }
}
