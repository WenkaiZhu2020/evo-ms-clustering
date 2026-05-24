package org.evomicro.sootextractor;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertTrue;

import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.List;
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

  private Path compileFixture() throws IOException {
    Path sourceRoot = tempDir.resolve("src");
    Path packageDir = sourceRoot.resolve("com/example");
    Files.createDirectories(packageDir);
    writeSource(packageDir.resolve("I.java"), "package com.example; public interface I {}");
    writeSource(packageDir.resolve("Base.java"), "package com.example; public class Base {}");
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
            packageDir.resolve("Base.java").toString(),
            packageDir.resolve("B.java").toString(),
            packageDir.resolve("C.java").toString(),
            noiseDir.resolve("Primitive.java").toString(),
            packageDir.resolve("A.java").toString());
    assertEquals(0, exitCode);
    return classesDir;
  }

  private static void writeSource(Path path, String source) throws IOException {
    Files.writeString(path, source, StandardCharsets.UTF_8);
  }
}
