package org.evomicro.sootextractor;

import java.io.BufferedWriter;
import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.LinkedHashSet;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.stream.Stream;
import soot.ArrayType;
import soot.Body;
import soot.G;
import soot.Local;
import soot.RefType;
import soot.Scene;
import soot.SootClass;
import soot.SootField;
import soot.SootMethod;
import soot.Type;
import soot.Unit;
import soot.Value;
import soot.jimple.AssignStmt;
import soot.jimple.CastExpr;
import soot.jimple.IdentityStmt;
import soot.jimple.InvokeExpr;
import soot.jimple.NewExpr;
import soot.jimple.ParameterRef;
import soot.jimple.Stmt;
import soot.options.Options;
import soot.shimple.Shimple;
import soot.shimple.ShimpleBody;
import soot.shimple.toolkits.scalar.ShimpleLocalDefs;
import soot.shimple.toolkits.scalar.ShimpleLocalUses;
import soot.toolkits.scalar.UnitValueBoxPair;

public final class SootExtractorCli {
  static final List<String> CLASS_NODES_COLUMNS = List.of("class_id", "class_name", "package", "class_file_path");
  static final List<String> STRUCTURAL_DEPENDENCY_COLUMNS =
      List.of("source", "target", "dependency_type", "weight", "evidence_kind", "evidence_location");
  static final List<String> SSA_FLOW_COLUMNS =
      List.of("source", "target", "flow_type", "weight", "evidence_method", "evidence_statement");

  private SootExtractorCli() {}

  public static void main(String[] args) {
    System.exit(run(args));
  }

  public static int run(String[] args) {
    Map<String, String> options;
    try {
      options = parseArgs(args);
    } catch (IllegalArgumentException error) {
      System.err.println("ERROR: " + error.getMessage());
      printUsage();
      return 2;
    }

    Path classesDir = Path.of(options.get("--classes-dir"));
    Path outDir = Path.of(options.get("--out-dir"));
    List<String> appPackages = parseAppPackages(options.get("--app-packages"));

    if (!Files.isDirectory(classesDir)) {
      System.err.println("ERROR: --classes-dir does not exist or is not a directory: " + classesDir);
      return 2;
    }
    if (appPackages.isEmpty()) {
      System.err.println("ERROR: --app-packages must contain at least one package prefix");
      return 2;
    }

    try {
      List<String> applicationClasses = discoverApplicationClasses(classesDir, appPackages);
      Set<String> applicationClassSet = new LinkedHashSet<>(applicationClasses);
      ExtractionResult result =
          extractStructuralDependencies(classesDir, options.get("--classpath"), applicationClasses, applicationClassSet);
      Files.createDirectories(outDir);
      writeClassNodes(outDir.resolve("class_nodes.csv"), result.classNodes());
      writeStructuralDependencies(outDir.resolve("structural_dependencies.csv"), result.structuralDependencies());
      writeSsaFlowEdges(outDir.resolve("ssa_flow_edges.csv"), result.ssaFlowEdges());

      System.out.println("subject=" + options.get("--subject"));
      System.out.println("classes_dir=" + classesDir);
      System.out.println("classpath=" + options.get("--classpath"));
      System.out.println("app_packages=" + String.join(",", appPackages));
      System.out.println("application_classes_detected=" + result.classNodes().size());
      System.out.println("structural_dependencies_extracted=" + result.structuralDependencies().size());
      System.out.println("ssa_flow_edges_extracted=" + result.ssaFlowEdges().size());
      System.out.println("out_dir=" + outDir);
      return 0;
    } catch (IOException error) {
      System.err.println("ERROR: failed to write normalized CSV outputs: " + error.getMessage());
      return 1;
    }
  }

  static ExtractionResult extractStructuralDependencies(
      Path classesDir, String classpath, List<String> applicationClasses, Set<String> applicationClassSet) {
    G.reset();
    Options.v().set_allow_phantom_refs(true);
    Options.v().set_ignore_resolution_errors(true);
    Options.v().set_no_bodies_for_excluded(true);
    Options.v().set_prepend_classpath(true);
    Options.v().set_process_dir(List.of(classesDir.toString()));
    Options.v().set_soot_classpath(classpath);
    Options.v().set_src_prec(Options.src_prec_only_class);
    Options.v().set_output_format(Options.output_format_none);

    for (String className : applicationClasses) {
      SootClass sootClass = Scene.v().forceResolve(className, SootClass.BODIES);
      sootClass.setApplicationClass();
    }
    Scene.v().loadNecessaryClasses();

    List<ClassNode> classNodes = new ArrayList<>();
    Set<StructuralDependency> structuralDependencies = new LinkedHashSet<>();
    Set<FlowEdge> ssaFlowEdges = new LinkedHashSet<>();

    for (String className : applicationClasses) {
      SootClass sootClass = Scene.v().getSootClass(className);
      classNodes.add(classNode(classesDir, className));
      extractTypeDependencies(sootClass, applicationClassSet, structuralDependencies);
      extractCallDependencies(sootClass, applicationClassSet, structuralDependencies);
      extractSsaFlowEdges(sootClass, applicationClassSet, ssaFlowEdges);
    }

    return new ExtractionResult(classNodes, new ArrayList<>(structuralDependencies), new ArrayList<>(ssaFlowEdges));
  }

  private static ClassNode classNode(Path classesDir, String className) {
    String packageName = packageName(className);
    Path classFile = classesDir.resolve(className.replace('.', '/') + ".class");
    return new ClassNode(className, className, packageName, classFile.toString());
  }

  private static String packageName(String className) {
    int index = className.lastIndexOf('.');
    return index < 0 ? "" : className.substring(0, index);
  }

  private static void extractTypeDependencies(
      SootClass sootClass, Set<String> applicationClassSet, Set<StructuralDependency> dependencies) {
    String source = sootClass.getName();
    if (sootClass.hasSuperclass()) {
      addTypeDependency(
          source,
          sootClass.getSuperclass().getName(),
          applicationClassSet,
          dependencies,
          "extends_type_reference",
          source);
    }
    for (SootClass iface : sootClass.getInterfaces()) {
      addTypeDependency(source, iface.getName(), applicationClassSet, dependencies, "implements_type_reference", source);
    }
    for (SootField field : sootClass.getFields()) {
      addTypeDependency(
          source,
          field.getType(),
          applicationClassSet,
          dependencies,
          "field_type_reference",
          source + "." + field.getName());
    }
    for (SootMethod method : sootClass.getMethods()) {
      String methodSignature = method.getSignature();
      addTypeDependency(
          source,
          method.getReturnType(),
          applicationClassSet,
          dependencies,
          "method_return_type_reference",
          methodSignature);
      for (Type parameterType : method.getParameterTypes()) {
        addTypeDependency(
            source,
            parameterType,
            applicationClassSet,
            dependencies,
            "method_parameter_type_reference",
            methodSignature);
      }
    }
  }

  private static void addTypeDependency(
      String source,
      Type type,
      Set<String> applicationClassSet,
      Set<StructuralDependency> dependencies,
      String evidenceKind,
      String evidenceLocation) {
    String target = classNameFromType(type);
    if (target != null) {
      addTypeDependency(source, target, applicationClassSet, dependencies, evidenceKind, evidenceLocation);
    }
  }

  private static void addTypeDependency(
      String source,
      String target,
      Set<String> applicationClassSet,
      Set<StructuralDependency> dependencies,
      String evidenceKind,
      String evidenceLocation) {
    if (!source.equals(target) && applicationClassSet.contains(target)) {
      dependencies.add(new StructuralDependency(source, target, "type", "1", evidenceKind, evidenceLocation));
    }
  }

  private static String classNameFromType(Type type) {
    if (type instanceof RefType refType) {
      return refType.getClassName();
    }
    if (type instanceof ArrayType arrayType) {
      return classNameFromType(arrayType.baseType);
    }
    return null;
  }

  private static void extractCallDependencies(
      SootClass sootClass, Set<String> applicationClassSet, Set<StructuralDependency> dependencies) {
    String source = sootClass.getName();
    for (SootMethod method : sootClass.getMethods()) {
      if (!method.isConcrete()) {
        continue;
      }
      Body body;
      try {
        body = method.retrieveActiveBody();
      } catch (RuntimeException error) {
        System.err.println("WARNING: could not retrieve Jimple body for " + method.getSignature() + ": " + error.getMessage());
        continue;
      }
      for (Unit unit : body.getUnits()) {
        if (!(unit instanceof Stmt stmt) || !stmt.containsInvokeExpr()) {
          continue;
        }
        try {
          InvokeExpr invokeExpr = stmt.getInvokeExpr();
          SootMethod targetMethod = invokeExpr.getMethod();
          String targetClass = targetMethod.getDeclaringClass().getName();
          if (!source.equals(targetClass) && applicationClassSet.contains(targetClass)) {
            dependencies.add(
                new StructuralDependency(
                    source,
                    targetClass,
                    "call",
                    "2",
                    "method_call",
                    method.getSignature() + " :: " + stmt));
          }
        } catch (RuntimeException error) {
          System.err.println("WARNING: could not resolve invoke target in " + method.getSignature() + ": " + error.getMessage());
        }
      }
    }
  }

  private static void extractSsaFlowEdges(SootClass sootClass, Set<String> applicationClassSet, Set<FlowEdge> flowEdges) {
    for (SootMethod method : sootClass.getMethods()) {
      if (!method.isConcrete()) {
        continue;
      }
      Body jimpleBody;
      try {
        jimpleBody = method.retrieveActiveBody();
      } catch (RuntimeException error) {
        System.err.println(
            "WARNING: could not retrieve Jimple body for SSA flow extraction in "
                + method.getSignature()
                + ": "
                + error.getMessage());
        continue;
      }

      ShimpleBody shimpleBody;
      try {
        shimpleBody = Shimple.v().newBody(jimpleBody);
      } catch (RuntimeException error) {
        System.err.println(
            "WARNING: could not convert method body to Shimple for "
                + method.getSignature()
                + ": "
                + error.getMessage());
        continue;
      }

      ShimpleLocalDefs localDefs = new ShimpleLocalDefs(shimpleBody);
      ShimpleLocalUses localUses = new ShimpleLocalUses(shimpleBody);
      extractReturnValueFlows(method, shimpleBody, localUses, applicationClassSet, flowEdges);
      extractArgumentPassingFlows(method, shimpleBody, localDefs, applicationClassSet, flowEdges);
    }
  }

  private static void extractReturnValueFlows(
      SootMethod method,
      ShimpleBody shimpleBody,
      ShimpleLocalUses localUses,
      Set<String> applicationClassSet,
      Set<FlowEdge> flowEdges) {
    for (Unit unit : shimpleBody.getUnits()) {
      if (!(unit instanceof AssignStmt assignStmt) || !(assignStmt.getLeftOp() instanceof Local definedLocal)) {
        continue;
      }
      if (!assignStmt.containsInvokeExpr()) {
        continue;
      }

      String sourceClass = applicationInvokeTarget(assignStmt.getInvokeExpr(), applicationClassSet);
      if (sourceClass == null) {
        continue;
      }

      for (UnitValueBoxPair use : localUses.getUsesOf(definedLocal)) {
        Unit useUnit = use.getUnit();
        if (!(useUnit instanceof Stmt useStmt) || !useStmt.containsInvokeExpr()) {
          continue;
        }
        if (!invokeUsesValueAsArgument(useStmt.getInvokeExpr(), definedLocal)) {
          continue;
        }
        String targetClass = applicationInvokeTarget(useStmt.getInvokeExpr(), applicationClassSet);
        if (targetClass == null) {
          System.err.println(
              "WARNING: skipping return_value_flow with unresolved application target in "
                  + method.getSignature()
                  + ": "
                  + useStmt);
          continue;
        }
        addFlowEdge(sourceClass, targetClass, "return_value_flow", method.getSignature(), useStmt.toString(), flowEdges);
      }
    }
  }

  private static void extractArgumentPassingFlows(
      SootMethod method,
      ShimpleBody shimpleBody,
      ShimpleLocalDefs localDefs,
      Set<String> applicationClassSet,
      Set<FlowEdge> flowEdges) {
    for (Unit unit : shimpleBody.getUnits()) {
      if (!(unit instanceof Stmt stmt) || !stmt.containsInvokeExpr()) {
        continue;
      }
      InvokeExpr invokeExpr = stmt.getInvokeExpr();
      String targetClass = applicationInvokeTarget(invokeExpr, applicationClassSet);
      if (targetClass == null) {
        continue;
      }
      for (Value argument : invokeExpr.getArgs()) {
        String sourceClass = sourceClassForArgument(argument, unit, localDefs, applicationClassSet);
        if (sourceClass == null) {
          System.err.println(
              "WARNING: skipping argument_passing_flow with unresolved source in "
                  + method.getSignature()
                  + ": "
                  + stmt);
          continue;
        }
        addFlowEdge(sourceClass, targetClass, "argument_passing_flow", method.getSignature(), stmt.toString(), flowEdges);
      }
    }
  }

  private static String sourceClassForArgument(
      Value argument, Unit useUnit, ShimpleLocalDefs localDefs, Set<String> applicationClassSet) {
    String directType = applicationClassNameFromType(argument.getType(), applicationClassSet);
    if (!(argument instanceof Local local)) {
      return directType;
    }

    for (Unit defUnit : localDefs.getDefsOfAt(local, useUnit)) {
      String sourceClass = sourceClassFromDefinition(defUnit, applicationClassSet);
      if (sourceClass != null) {
        return sourceClass;
      }
    }
    return directType;
  }

  private static String sourceClassFromDefinition(Unit defUnit, Set<String> applicationClassSet) {
    if (defUnit instanceof IdentityStmt identityStmt && identityStmt.getRightOp() instanceof ParameterRef parameterRef) {
      return applicationClassNameFromType(parameterRef.getType(), applicationClassSet);
    }
    if (!(defUnit instanceof AssignStmt assignStmt)) {
      return null;
    }
    if (assignStmt.containsInvokeExpr()) {
      return applicationInvokeTarget(assignStmt.getInvokeExpr(), applicationClassSet);
    }
    Value right = assignStmt.getRightOp();
    if (right instanceof NewExpr newExpr) {
      return applicationClassNameFromType(newExpr.getType(), applicationClassSet);
    }
    if (right instanceof CastExpr castExpr) {
      return applicationClassNameFromType(castExpr.getCastType(), applicationClassSet);
    }
    return applicationClassNameFromType(right.getType(), applicationClassSet);
  }

  private static String applicationInvokeTarget(InvokeExpr invokeExpr, Set<String> applicationClassSet) {
    try {
      String targetClass = invokeExpr.getMethod().getDeclaringClass().getName();
      return applicationClassSet.contains(targetClass) ? targetClass : null;
    } catch (RuntimeException error) {
      return null;
    }
  }

  private static String applicationClassNameFromType(Type type, Set<String> applicationClassSet) {
    String className = classNameFromType(type);
    return className != null && applicationClassSet.contains(className) ? className : null;
  }

  private static boolean invokeUsesValueAsArgument(InvokeExpr invokeExpr, Value value) {
    for (Value argument : invokeExpr.getArgs()) {
      if (argument.equivTo(value)) {
        return true;
      }
    }
    return false;
  }

  private static void addFlowEdge(
      String source,
      String target,
      String flowType,
      String evidenceMethod,
      String evidenceStatement,
      Set<FlowEdge> flowEdges) {
    if (!source.equals(target)) {
      flowEdges.add(new FlowEdge(source, target, flowType, "3", evidenceMethod, evidenceStatement));
    }
  }

  static Map<String, String> parseArgs(String[] args) {
    Map<String, String> options = new LinkedHashMap<>();
    for (int index = 0; index < args.length; index++) {
      String key = args[index];
      if (!key.startsWith("--")) {
        throw new IllegalArgumentException("unexpected positional argument: " + key);
      }
      if (index + 1 >= args.length || args[index + 1].startsWith("--")) {
        throw new IllegalArgumentException("missing value for " + key);
      }
      options.put(key, args[++index]);
    }

    for (String required : List.of("--subject", "--classes-dir", "--classpath", "--app-packages", "--out-dir")) {
      if (!options.containsKey(required)) {
        throw new IllegalArgumentException("missing required argument " + required);
      }
    }
    return options;
  }

  static List<String> parseAppPackages(String rawValue) {
    List<String> packages = new ArrayList<>();
    for (String value : rawValue.split(",")) {
      String packageName = value.trim();
      if (!packageName.isEmpty()) {
        packages.add(packageName);
      }
    }
    return packages;
  }

  static List<String> discoverApplicationClasses(Path classesDir, List<String> appPackages) throws IOException {
    try (Stream<Path> files = Files.walk(classesDir)) {
      return files
          .filter(path -> Files.isRegularFile(path) && path.toString().endsWith(".class"))
          .map(path -> classNameFromFile(classesDir, path))
          .filter(className -> isApplicationClass(className, appPackages))
          .sorted()
          .toList();
    }
  }

  static String classNameFromFile(Path classesDir, Path classFile) {
    Path relativePath = classesDir.relativize(classFile);
    String withoutSuffix = relativePath.toString().replaceAll("\\.class$", "");
    return withoutSuffix.replace('/', '.').replace('\\', '.');
  }

  static boolean isApplicationClass(String className, List<String> appPackages) {
    return appPackages.stream()
        .anyMatch(packageName -> className.equals(packageName) || className.startsWith(packageName + "."));
  }

  static void writeHeader(Path path, List<String> columns) throws IOException {
    try (BufferedWriter writer = Files.newBufferedWriter(path, StandardCharsets.UTF_8)) {
      writer.write(String.join(",", columns));
      writer.newLine();
    }
  }

  static void writeClassNodes(Path path, List<ClassNode> classNodes) throws IOException {
    try (BufferedWriter writer = Files.newBufferedWriter(path, StandardCharsets.UTF_8)) {
      writer.write(String.join(",", CLASS_NODES_COLUMNS));
      writer.newLine();
      for (ClassNode classNode : classNodes) {
        writer.write(csvRow(classNode.classId(), classNode.className(), classNode.packageName(), classNode.classFilePath()));
        writer.newLine();
      }
    }
  }

  static void writeStructuralDependencies(Path path, List<StructuralDependency> dependencies) throws IOException {
    try (BufferedWriter writer = Files.newBufferedWriter(path, StandardCharsets.UTF_8)) {
      writer.write(String.join(",", STRUCTURAL_DEPENDENCY_COLUMNS));
      writer.newLine();
      for (StructuralDependency dependency : dependencies) {
        writer.write(
            csvRow(
                dependency.source(),
                dependency.target(),
                dependency.dependencyType(),
                dependency.weight(),
                dependency.evidenceKind(),
                dependency.evidenceLocation()));
        writer.newLine();
      }
    }
  }

  static void writeSsaFlowEdges(Path path, List<FlowEdge> flowEdges) throws IOException {
    try (BufferedWriter writer = Files.newBufferedWriter(path, StandardCharsets.UTF_8)) {
      writer.write(String.join(",", SSA_FLOW_COLUMNS));
      writer.newLine();
      for (FlowEdge flowEdge : flowEdges) {
        writer.write(
            csvRow(
                flowEdge.source(),
                flowEdge.target(),
                flowEdge.flowType(),
                flowEdge.weight(),
                flowEdge.evidenceMethod(),
                flowEdge.evidenceStatement()));
        writer.newLine();
      }
    }
  }

  private static String csvRow(String... values) {
    return Stream.of(values).map(SootExtractorCli::csvValue).reduce((left, right) -> left + "," + right).orElse("");
  }

  private static String csvValue(String value) {
    if (value == null) {
      return "";
    }
    boolean quote = value.contains(",") || value.contains("\"") || value.contains("\n") || value.contains("\r");
    String escaped = value.replace("\"", "\"\"");
    return quote ? "\"" + escaped + "\"" : escaped;
  }

  private static void printUsage() {
    System.err.println(
        "Usage: java org.evomicro.sootextractor.SootExtractorCli "
            + "--subject <name> --classes-dir <dir> --classpath <classpath> "
            + "--app-packages <pkg[,pkg...]> --out-dir <dir>");
  }

  record ClassNode(String classId, String className, String packageName, String classFilePath) {}

  record StructuralDependency(
      String source, String target, String dependencyType, String weight, String evidenceKind, String evidenceLocation) {}

  record FlowEdge(
      String source, String target, String flowType, String weight, String evidenceMethod, String evidenceStatement) {}

  record ExtractionResult(
      List<ClassNode> classNodes, List<StructuralDependency> structuralDependencies, List<FlowEdge> ssaFlowEdges) {}
}
