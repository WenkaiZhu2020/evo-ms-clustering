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
import soot.Modifier;
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
import soot.tagkit.AnnotationTag;
import soot.tagkit.SyntheticTag;
import soot.toolkits.scalar.UnitValueBoxPair;

/**
 * Command-line Soot/Shimple extractor that writes normalized Stage 1 CSV inputs.
 *
 * <p>The extractor emits class nodes, structural dependency evidence, and scoped SSA flow evidence for configured
 * application package prefixes.
 */
public final class SootExtractorCli {
  static final List<String> CLASS_NODES_COLUMNS = List.of("class_id", "class_name", "package", "class_file_path");
  static final List<String> STRUCTURAL_DEPENDENCY_COLUMNS =
      List.of("source", "target", "dependency_type", "weight", "evidence_kind", "evidence_location");
  static final List<String> SSA_FLOW_COLUMNS =
      List.of("source", "target", "flow_type", "weight", "evidence_method", "evidence_statement");
  static final List<String> METHOD_BODY_COLUMNS =
      List.of("class_id", "method_name", "method_signature", "concrete", "synthetic", "body_text");
  static final List<String> SEMANTIC_INPUT_COLUMNS =
      List.of(
          "subject",
          "class_id",
          "class_name",
          "kind",
          "superclass_present",
          "semantic_text",
          "method_count",
          "annotation_count",
          "interface_count",
          "input_hash");
  private static final int JAVA_BRIDGE_MODIFIER = 0x40;

  private SootExtractorCli() {}

  public static void main(String[] args) {
    System.exit(run(args));
  }

  /** Parses CLI options, runs extraction, and writes the three normalized CSV tables. */
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
    Path semanticOut =
        Path.of(options.getOrDefault("--semantic-out", outDir.resolve("class_declarations.csv").toString()));
    List<String> appPackages = parseAppPackages(options.get("--app-packages"));
    List<String> excludePackages = parseAppPackages(options.getOrDefault("--exclude-packages", ""));

    if (!Files.isDirectory(classesDir)) {
      System.err.println("ERROR: --classes-dir does not exist or is not a directory: " + classesDir);
      return 2;
    }
    if (appPackages.isEmpty()) {
      System.err.println("ERROR: --app-packages must contain at least one package prefix");
      return 2;
    }

    try {
      List<String> applicationClasses = discoverApplicationClasses(classesDir, appPackages, excludePackages);
      Set<String> applicationClassSet = new LinkedHashSet<>(applicationClasses);
      ExtractionResult result =
          extractStructuralDependencies(classesDir, options.get("--classpath"), applicationClasses, applicationClassSet);
      Files.createDirectories(outDir);
      if (semanticOut.getParent() != null) {
        Files.createDirectories(semanticOut.getParent());
      }
      writeClassNodes(outDir.resolve("class_nodes.csv"), result.classNodes());
      writeStructuralDependencies(outDir.resolve("structural_dependencies.csv"), result.structuralDependencies());
      writeSsaFlowEdges(outDir.resolve("ssa_flow_edges.csv"), result.ssaFlowEdges());
      String methodBodyOutput = options.get("--method-body-out");
      if (methodBodyOutput != null) {
        Path methodBodyPath = Path.of(methodBodyOutput);
        if (methodBodyPath.getParent() != null) {
          Files.createDirectories(methodBodyPath.getParent());
        }
        writeMethodBodyEvidence(methodBodyPath, result.methodBodies());
      }
      writeSemanticInputs(
          semanticOut, options.get("--subject"), result.semanticInputs());

      System.out.println("subject=" + options.get("--subject"));
      System.out.println("classes_dir=" + classesDir);
      System.out.println("classpath=" + options.get("--classpath"));
      System.out.println("app_packages=" + String.join(",", appPackages));
      System.out.println("exclude_packages=" + String.join(",", excludePackages));
      System.out.println("application_classes_detected=" + result.classNodes().size());
      System.out.println("structural_dependencies_extracted=" + result.structuralDependencies().size());
      System.out.println("ssa_flow_edges_extracted=" + result.ssaFlowEdges().size());
      if (methodBodyOutput != null) {
        System.out.println("method_bodies_extracted=" + result.methodBodies().size());
        System.out.println("method_body_out=" + methodBodyOutput);
      }
      System.out.println("class_declarations_extracted=" + result.semanticInputs().size());
      System.out.println("out_dir=" + outDir);
      System.out.println("semantic_out=" + semanticOut);
      return 0;
    } catch (IOException error) {
      System.err.println("ERROR: failed to write normalized CSV outputs: " + error.getMessage());
      return 1;
    }
  }

  /** Configures Soot and extracts all class-level evidence for the selected application classes. */
  static ExtractionResult extractStructuralDependencies(
      Path classesDir, String classpath, List<String> applicationClasses, Set<String> applicationClassSet) {
    G.reset();

    // Keep Soot tolerant of missing framework classes in small subject builds.
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
    List<MethodBodyEvidence> methodBodies = new ArrayList<>();
    List<ClassDeclaration> semanticInputs = new ArrayList<>();

    for (String className : applicationClasses) {
      SootClass sootClass = Scene.v().getSootClass(className);
      classNodes.add(classNode(classesDir, className));
      semanticInputs.add(classDeclaration(sootClass));
      methodBodies.addAll(extractMethodBodies(sootClass));
      extractTypeDependencies(sootClass, applicationClassSet, structuralDependencies);
      extractCallDependencies(sootClass, applicationClassSet, structuralDependencies);
      extractSsaFlowEdges(sootClass, applicationClassSet, ssaFlowEdges);
    }

    semanticInputs.sort(java.util.Comparator.comparing(ClassDeclaration::classId));
    return new ExtractionResult(
        classNodes,
        new ArrayList<>(structuralDependencies),
        new ArrayList<>(ssaFlowEdges),
        methodBodies,
        semanticInputs);
  }

  /** Extracts canonical Shimple text for later lexical normalization; no graph evidence is emitted here. */
  private static List<MethodBodyEvidence> extractMethodBodies(SootClass sootClass) {
    List<MethodBodyEvidence> extracted = new ArrayList<>();
    for (SootMethod method : sootClass.getMethods()) {
      if (!method.isConcrete()) {
        continue;
      }
      Body jimpleBody;
      try {
        jimpleBody = method.retrieveActiveBody();
      } catch (RuntimeException error) {
        System.err.println("WARNING: could not retrieve Jimple body for method-body evidence " + method.getSignature() + ": " + error.getMessage());
        continue;
      }
      try {
        ShimpleBody shimpleBody = Shimple.v().newBody(jimpleBody);
        StringBuilder text = new StringBuilder();
        for (Unit unit : shimpleBody.getUnits()) {
          text.append(unit).append('\n');
        }
        extracted.add(
            new MethodBodyEvidence(
                sootClass.getName(),
                method.getName(),
                method.getSignature(),
                true,
                Modifier.isSynthetic(method.getModifiers())
                    || method.getTags().stream().anyMatch(tag -> tag instanceof SyntheticTag),
                text.toString()));
      } catch (RuntimeException error) {
        System.err.println("WARNING: could not convert method body to Shimple for method-body evidence " + method.getSignature() + ": " + error.getMessage());
      }
    }
    extracted.sort(
        java.util.Comparator.comparing(MethodBodyEvidence::classId)
            .thenComparing(MethodBodyEvidence::methodName)
            .thenComparing(MethodBodyEvidence::methodSignature));
    return extracted;
  }

  static ClassDeclaration classDeclaration(SootClass sootClass) {
    List<String> annotations = classAnnotations(sootClass);
    List<String> interfaces = sootClass.getInterfaces().stream()
        .map(SootClass::getName)
        .map(SootExtractorCli::simpleName)
        .distinct()
        .sorted()
        .toList();
    String superclass = meaningfulSuperclass(sootClass);
    List<String> methods = sootClass.getMethods().stream()
        .filter(SootExtractorCli::includeMethod)
        .map(SootExtractorCli::renderMethod)
        .distinct()
        .sorted(java.util.Comparator.comparing(SootExtractorCli::methodName).thenComparing(String::compareTo))
        .toList();

    String kind = entityKind(sootClass);
    StringBuilder text = new StringBuilder();
    for (String annotation : annotations) {
      text.append('@').append(annotation).append('\n');
    }
    if (sootClass.isPublic()) {
      text.append("public ");
    }
    text.append(kind).append(' ').append(simpleName(sootClass.getName()));
    if (superclass != null) {
      text.append(" extends ").append(superclass);
    }
    if (!interfaces.isEmpty()) {
      text.append(sootClass.isInterface() ? " extends " : " implements ");
      text.append(String.join(", ", interfaces));
    }
    text.append(" {\n");
    for (String method : methods) {
      text.append("    ").append(method).append('\n');
    }
    text.append("}\n");

    String semanticText = text.toString();
    return new ClassDeclaration(
        sootClass.getName(),
        simpleName(sootClass.getName()),
        kind,
        superclass != null,
        semanticText,
        methods.size(),
        annotations.size(),
        interfaces.size(),
        sha256(semanticText));
  }

  private static String entityKind(SootClass sootClass) {
    if (sootClass.isEnum()) {
      return "enum";
    }
    if (sootClass.isInterface()) {
      return "interface";
    }
    return sootClass.isAbstract() ? "abstract class" : "class";
  }

  private static String meaningfulSuperclass(SootClass sootClass) {
    if (!sootClass.hasSuperclass()) {
      return null;
    }
    String superclass = sootClass.getSuperclass().getName();
    if (superclass.equals("java.lang.Object") || superclass.equals("java.lang.Enum")) {
      return null;
    }
    return simpleName(superclass);
  }

  private static List<String> classAnnotations(SootClass sootClass) {
    return sootClass.getTags().stream()
        .filter(tag -> tag instanceof soot.tagkit.VisibilityAnnotationTag)
        .map(tag -> (soot.tagkit.VisibilityAnnotationTag) tag)
        .flatMap(tag -> tag.getAnnotations().stream())
        .map(AnnotationTag::getType)
        .map(SootExtractorCli::normalizeAnnotationName)
        .distinct()
        .sorted()
        .toList();
  }

  private static String normalizeAnnotationName(String value) {
    String normalized = value;
    if (normalized.startsWith("L") && normalized.endsWith(";")) {
      normalized = normalized.substring(1, normalized.length() - 1);
    }
    return simpleName(normalized.replace('/', '.'));
  }

  private static boolean includeMethod(SootMethod method) {
    return !method.isConstructor()
        && !method.isStaticInitializer()
        && !Modifier.isSynthetic(method.getModifiers())
        && (method.getModifiers() & JAVA_BRIDGE_MODIFIER) == 0
        && method.getTags().stream().noneMatch(tag -> tag instanceof SyntheticTag);
  }

  private static String renderMethod(SootMethod method) {
    String parameters = method.getParameterTypes().stream()
        .map(SootExtractorCli::normalizeType)
        .reduce((left, right) -> left + ", " + right)
        .orElse("");
    return normalizeType(method.getReturnType()) + " " + method.getName() + "(" + parameters + ");";
  }

  private static String methodName(String renderedMethod) {
    return renderedMethod.substring(renderedMethod.indexOf(' ') + 1, renderedMethod.indexOf('('));
  }

  static String normalizeType(Type type) {
    if (type instanceof ArrayType arrayType) {
      return normalizeType(arrayType.baseType) + "[]".repeat(arrayType.numDimensions);
    }
    if (type instanceof RefType refType) {
      return simpleName(refType.getClassName());
    }
    return simpleName(type.toString());
  }

  static String simpleName(String name) {
    String normalized = name.replace('/', '.');
    int separator = normalized.lastIndexOf('.');
    return separator < 0 ? normalized : normalized.substring(separator + 1);
  }

  private static String sha256(String value) {
    try {
      java.security.MessageDigest digest = java.security.MessageDigest.getInstance("SHA-256");
      byte[] bytes = digest.digest(value.getBytes(StandardCharsets.UTF_8));
      StringBuilder result = new StringBuilder(bytes.length * 2);
      for (byte valueByte : bytes) {
        result.append(String.format("%02x", valueByte));
      }
      return result.toString();
    } catch (java.security.NoSuchAlgorithmException error) {
      throw new IllegalStateException("SHA-256 is unavailable", error);
    }
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

  /** Extracts declaration-level type references for G_raw structural evidence. */
  private static void extractTypeDependencies(
      SootClass sootClass, Set<String> applicationClassSet, Set<StructuralDependency> dependencies) {
    String source = sootClass.getName();

    // Type evidence comes from declarations, not local variables.
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
      addTypeDependency(
        source, 
        iface.getName(), 
        applicationClassSet, 
        dependencies, 
        "implements_type_reference", 
        source);
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

  /** Extracts method-call evidence from Jimple bodies for G_raw structural edges. */
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
          // Calls are class-level edges: caller class to callee declaring class.
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

  /** Converts concrete method bodies to Shimple and extracts scoped SSA flow patterns. */
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

      // Stage 1 keeps only two SSA patterns that map cleanly to class pairs.
      extractReturnValueFlows(method, shimpleBody, localUses, applicationClassSet, flowEdges);
      extractArgumentPassingFlows(method, shimpleBody, localDefs, applicationClassSet, flowEdges);
    }
  }

  /** Records return-value flow when one application call result is passed into another application call. */
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

      // A call result used as an argument to another app call becomes B -> C.
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

  /** Records argument-passing flow from a resolved application source class to an invoked application class. */
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
        // Prefer the argument's definition; fall back to its declared app type.
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
    return discoverApplicationClasses(classesDir, appPackages, List.of());
  }

  /** Discovers compiled classes that match the configured include and exclude package prefixes. */
  static List<String> discoverApplicationClasses(Path classesDir, List<String> appPackages, List<String> excludePackages)
      throws IOException {
    try (Stream<Path> files = Files.walk(classesDir)) {
      return files
          .filter(path -> Files.isRegularFile(path) && path.toString().endsWith(".class"))
          .map(path -> classNameFromFile(classesDir, path))
          .filter(className -> isApplicationClass(className, appPackages, excludePackages))
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
    return isApplicationClass(className, appPackages, List.of());
  }

  static boolean isApplicationClass(String className, List<String> appPackages, List<String> excludePackages) {
    return appPackages.stream()
        .anyMatch(packageName -> className.equals(packageName) || className.startsWith(packageName + "."))
        && excludePackages.stream()
            .noneMatch(packageName -> className.equals(packageName) || className.startsWith(packageName + "."));
  }

  static void writeHeader(Path path, List<String> columns) throws IOException {
    try (BufferedWriter writer = Files.newBufferedWriter(path, StandardCharsets.UTF_8)) {
      writer.write(String.join(",", columns));
      writer.newLine();
    }
  }

  /** Writes class_nodes.csv using fully qualified class names as stable class ids. */
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

  /** Writes structural_dependencies.csv with type and call evidence rows. */
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

  /** Writes ssa_flow_edges.csv with return-value and argument-passing flow rows. */
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

  /** Writes method-body evidence separately from the frozen Stage 1/Stage 2 tables. */
  static void writeMethodBodyEvidence(Path path, List<MethodBodyEvidence> methodBodies) throws IOException {
    try (BufferedWriter writer = Files.newBufferedWriter(path, StandardCharsets.UTF_8)) {
      writer.write(String.join(",", METHOD_BODY_COLUMNS));
      writer.newLine();
      for (MethodBodyEvidence evidence : methodBodies) {
        writer.write(
            csvRow(
                evidence.classId(),
                evidence.methodName(),
                evidence.methodSignature(),
                Boolean.toString(evidence.concrete()),
                Boolean.toString(evidence.synthetic()),
                evidence.bodyText()));
        writer.newLine();
      }
    }
  }

  static void writeSemanticInputs(Path path, String subject, List<ClassDeclaration> declarations) throws IOException {
    List<ClassDeclaration> sorted = declarations.stream()
        .sorted(java.util.Comparator.comparing(ClassDeclaration::classId))
        .toList();
    try (BufferedWriter writer = Files.newBufferedWriter(path, StandardCharsets.UTF_8)) {
      writer.write(String.join(",", SEMANTIC_INPUT_COLUMNS));
      writer.write("\n");
      for (ClassDeclaration declaration : sorted) {
        writer.write(
            csvRow(
                subject,
                declaration.classId(),
                declaration.className(),
                declaration.kind(),
                Boolean.toString(declaration.superclassPresent()),
                declaration.semanticText(),
                Integer.toString(declaration.methodCount()),
                Integer.toString(declaration.annotationCount()),
                Integer.toString(declaration.interfaceCount()),
                declaration.inputHash()));
        writer.write("\n");
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
    // Minimal CSV escaping for statements and method signatures.
    boolean quote = value.contains(",") || value.contains("\"") || value.contains("\n") || value.contains("\r");
    String escaped = value.replace("\"", "\"\"");
    return quote ? "\"" + escaped + "\"" : escaped;
  }

  private static void printUsage() {
    System.err.println(
        "Usage: java org.evomicro.sootextractor.SootExtractorCli "
            + "--subject <name> --classes-dir <dir> --classpath <classpath> "
            + "--app-packages <pkg[,pkg...]> [--exclude-packages <pkg[,pkg...]>] --out-dir <dir> "
            + "[--semantic-out <csv>]");
  }

  record ClassNode(String classId, String className, String packageName, String classFilePath) {}

  record StructuralDependency(
      String source, String target, String dependencyType, String weight, String evidenceKind, String evidenceLocation) {}

  record FlowEdge(
      String source, String target, String flowType, String weight, String evidenceMethod, String evidenceStatement) {}

  record ExtractionResult(
      List<ClassNode> classNodes,
      List<StructuralDependency> structuralDependencies,
      List<FlowEdge> ssaFlowEdges,
      List<MethodBodyEvidence> methodBodies,
      List<ClassDeclaration> semanticInputs) {}

  record MethodBodyEvidence(
      String classId,
      String methodName,
      String methodSignature,
      boolean concrete,
      boolean synthetic,
      String bodyText) {}

  record ClassDeclaration(
      String classId,
      String className,
      String kind,
      boolean superclassPresent,
      String semanticText,
      int methodCount,
      int annotationCount,
      int interfaceCount,
      String inputHash) {}
}
