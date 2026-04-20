PS C:\Users\MaximilianNussbaumer\Workspace\mcp-generator-2.0> 
  // First pass: collect all files and their exported names
  const fileExports: Map<string, Set<string>> = new Map();

  for (const file of files) {
    if (file.isFile() && file.name.endsWith('.ts') && !file.name.endsWith('.d.ts') && file.name !== 'index.ts' && file.name !== 'ValidatorOptions.ts') {
      const filePath = path.join(dir, file.name);
      const content = fs.readFileSync(filePath, 'utf-8');
      const names = new Set<string>();

      const exportMatches = content.matchAll(/export\s+(?:interface|class|type|const|function)\s+(\w+)/g);
      for (const match of exportMatches) {
        names.add(match[1]);
      }

      fileExports.set(file.name, names);
    }
  }

  // Second pass: export files, using selective named exports when there are conflicts
  for (const file of files) {
    if (file.isFile() && file.name.endsWith('.ts') && !file.name.endsWith('.d.ts') && file.name !== 'index.ts' && file.name !== 'ValidatorOptions.ts') {
      const baseName = file.name.replace('.ts', '');
      const fileNames = fileExports.get(file.name) || new Set();

      // Find which names from this file conflict with already-exported names
      const conflicting = new Set<string>();
      const unique = new Set<string>();
      for (const name of fileNames) {
        if (exportedNames.has(name)) {
          conflicting.add(name);
        } else {
          unique.add(name);
        }
      }

      if (conflicting.size === 0) {
        // No conflicts — use simple wildcard export
        exports.push(`export * from './${baseName}.js';`);
      } else if (unique.size > 0) {
        // Has conflicts but also has unique names — use selective named export
        const names = [...unique].sort().join(', ');
        exports.push(`export { ${names} } from './${baseName}.js';`);
      }
      // If all names conflict (unique.size === 0), skip entirely

      // Track all names from this file as exported
      for (const name of fileNames) {
        exportedNames.add(name);
      }
    }
  }

  // Also export from valuesets subfolder if it exists
  const valueSetsDir = path.join(dir, 'valuesets');
  if (fs.existsSync(valueSetsDir)) {
    exports.push(`export * from './valuesets/index.js';`);
  }

  // Export shared ValidatorOptions type
  if (fs.existsSync(path.join(dir, 'ValidatorOptions.ts'))) {
    exports.push(`export type { ValidatorOptions } from './ValidatorOptions.js';`);
  }

  // Sort exports alphabetically for consistency
  exports.sort();

  const indexContent = `// Auto-generated index file - exports all generated FHIR profiles\n${exports.join('\n')}\n`;
  fs.writeFileSync(path.join(dir, 'index.ts'), indexContent, 'utf-8');
}

export async function generate(fhirSource: string, outputDir: string, flags?: GenerationFlags): Promise<void> {
  initGenerationContext(flags, outputDir);

  logger.log(`Fetching StructureDefinitions from: ${fhirSource}`);
  let structureDefinitions: StructureDefinition[] = [];
  let localPath = fhirSource;
  try {
    if (/^https?:\/\//.test(fhirSource)) {
      const tempTgz = path.join(process.cwd(), 'package.tgz');
      await downloadFile(fhirSource, tempTgz); localPath = tempTgz;
    }
  } catch { log.error(`Failed to download package from ${fhirSource}`); }
  let valueSetCodesMap: Record<string,{code:string;system?:string}[]>|undefined;
  let valueSets: Map<string, ParsedValueSet> | undefined;
  let referencedDepSDs: StructureDefinition[] = [];
  if (localPath.endsWith('.tgz') || localPath.endsWith('.zip')) {
    const extractResult = await extractPackage(localPath);
    const extracted = extractResult.path;
    const shouldCleanup = !extractResult.isCached;
    try {
      // Auto-detect FHIR version from package when not explicitly set
      if (!flags?.fhirVersion) {
        const detected = detectFhirVersion(extracted);
        if (detected) {
          await initVersionContext(detected);
        } else {
          await initVersionContext(DEFAULT_FHIR_VERSION);
        }
      } else {
        await initVersionContext(flags.fhirVersion);
      }

      structureDefinitions = readStructureDefinitionsFromDir(extracted);
      // Ensure dependency packages are downloaded before loading ValueSets
      await ensureDependenciesDownloaded(extracted);

      // Register SDs from dependency packages so external profile resolution can find them
      const depSDs = readStructureDefinitionsFromDependencies(extracted);
      registerLocalStructureDefinitions(depSDs);

      // Collect dependency profiles for cross-package delegation (validator-only)
      referencedDepSDs = collectReferencedDependencyProfiles(structureDefinitions, depSDs);

      // Load ValueSets from package AND its dependencies (for binding resolution)
      valueSetCodesMap = readValueSetCodesWithDependencies(extracted);
      valueSets = readValueSetsFromDir(extracted);
      logger.log(`Loaded ${valueSets.size} ValueSets (${Array.from(valueSets.values()).filter(vs => vs.isSmall).length} suitable for union types)`);
      logger.log(`Loaded ${Object.keys(valueSetCodesMap).length} ValueSet code mappings (including dependencies)`);

      // Enrich ValueSets with codes resolved from CodeSystems (system-only compose.include)
      // Only create new entries for ValueSets actually referenced by the profiles' bindings
      const allSDs = [...structureDefinitions, ...referencedDepSDs];
      const bindingUrls = collectValueSetBindingUrls(allSDs);
      enrichValueSetsFromCodeMap(valueSets, valueSetCodesMap, bindingUrls);
      
      // Expand ValueSets from terminology server if configured
      if (flags?.txServer) {
        valueSets = await expandValueSetsWithTx(valueSets, valueSetCodesMap, allSDs, flags.txServer, flags.displayLanguage);
      }
  } finally { if (shouldCleanup) { try { fs.rmSync(extracted,{recursive:true,force:true}); } catch { /* ignore cleanup errors */ } } }
  } else {
    // Non-package source (directory or URL): use explicit version flag or default
    await initVersionContext(flags?.fhirVersion ?? DEFAULT_FHIR_VERSION);
    structureDefinitions = await fetchStructureDefinitions(fhirSource);
  }
  const fhirInterfaceNames = ctx().interfaceNames;
  logger.log(`Fetched ${structureDefinitions.length} StructureDefinitions.`);
  ensureDirectoryExists(outputDir);
  const fhirChildTypeMap = buildFhirChildTypeMapFromJson();

  const { existingStructureDefinitions, profileIdToName, profileUrlToName, profileUrlToType } = buildProfileRegistries([...structureDefinitions, ...referencedDepSDs], fhirInterfaceNames);

  for (const sd of structureDefinitions) {
    await processStructureDefinition(sd, { outputDir, fhirSourceHint: fhirSource, valueSetCodesMap, valueSets, existingStructureDefinitions, profileIdToName, profileUrlToName, profileUrlToType, flags, fhirChildTypeMap });
  }
  // Process dependency SDs with noClasses (validator-only, no parity testing)
  if (referencedDepSDs.length > 0) {
    const depFlags = { ...flags, noClasses: true };
    for (const sd of referencedDepSDs) {
      await processStructureDefinition(sd, { outputDir, fhirSourceHint: '', valueSetCodesMap, valueSets, existingStructureDefinitions, profileIdToName, profileUrlToName, profileUrlToType, flags: depFlags, fhirChildTypeMap });
    }
  }
}

/**
 * New narrowed workflow: Accept a FHIR package archive (.tgz|.zip),
 * extract it, run generation on contained StructureDefinitions, place
 * generated TS artifacts under `generated/` inside the extracted package
 * folder, then repackage to the specified output archive (or alongside original).
 */
export async function generateIntoPackage(packageArchivePath: string, outArchivePath?: string, flags?: GenerationFlags): Promise<string> {
  initGenerationContext(flags, path.dirname(outArchivePath || packageArchivePath));
  resetTimings();

  if (!packageArchivePath.endsWith('.tgz') && !packageArchivePath.endsWith('.zip')) throw new Error('Only .tgz or .zip supported.');
  let endPhase = startPhase('extract');
  const extractResult = await extractPackage(packageArchivePath);
  const extractedRoot = extractResult.path;
  endPhase();
  const shouldCleanup = !extractResult.isCached; // Only cleanup temp directories, not cache
  try {
    // Auto-detect FHIR version from package when not explicitly set
    endPhase = startPhase('init');
    if (!flags?.fhirVersion) {
      const detected = detectFhirVersion(extractedRoot);
      await initVersionContext(detected ?? DEFAULT_FHIR_VERSION);
    } else {
      await initVersionContext(flags.fhirVersion);
    }
    const fhirInterfaceNames = ctx().interfaceNames;
    endPhase(); // init

    // Ensure dependency packages are downloaded BEFORE loading dependency SDs.
    // This is critical for CI (cold cache): without the download step, packages like
    // hrex won't be in the cache and cross-package profile delegation will silently
    // produce nothing — causing internal validators to miss delegated errors.
    endPhase = startPhase('resolve');
    await ensureDependenciesDownloaded(extractedRoot);

    // Load dependencies from package.json now that all deps are in the cache
    const { getPackageManager } = await import('./parser/packageManager.js');
    const packageManager = getPackageManager();
    packageManager.loadDependenciesFromExtractedPackage(extractedRoot);
    logger.log(`Loaded package dependencies (${packageManager.getTotalStructureDefinitionCount()} total SDs available)`);

    const structureDefinitions = readStructureDefinitionsFromDir(extractedRoot);

    // Collect dependency profiles referenced by main package's nested resource type
    // constraints (e.g., Parameters.parameter.part.resource → hrex-consent) for delegation
    const depPackageSDs = packageManager.getLoadedPackages().flatMap(p => p.structureDefinitions);
    const referencedDepSDs = collectReferencedDependencyProfiles(structureDefinitions, depPackageSDs);
    // Load ValueSets from package AND its dependencies (for binding resolution)
    const valueSetCodesMap = readValueSetCodesWithDependencies(extractedRoot);
    let valueSets = readValueSetsFromDir(extractedRoot);
    logger.log(`Package contains ${structureDefinitions.length} StructureDefinitions (+ ${referencedDepSDs.length} delegation deps).`);
    logger.log(`Loaded ${Object.keys(valueSetCodesMap).length} ValueSet code mappings (including dependencies)`);
    endPhase(); // resolve

    // Enrich ValueSets with codes resolved from CodeSystems (system-only compose.include)
    // Include dependency SDs for binding URL collection
    const allSDs = [...structureDefinitions, ...referencedDepSDs];
    const bindingUrls = collectValueSetBindingUrls(allSDs);
    enrichValueSetsFromCodeMap(valueSets, valueSetCodesMap, bindingUrls);
    
    // Expand ValueSets from terminology server if configured
    if (flags?.txServer) {
      valueSets = await expandValueSetsWithTx(valueSets, valueSetCodesMap, allSDs, flags.txServer, flags.displayLanguage);
    }
    
    const outputDir = path.join(extractedRoot, 'generated');
    // Always start with a clean generated/ directory to avoid stale compiled
    // artifacts (e.g. .d.ts/.js without .ts sources) from a cached extraction.
    if (fs.existsSync(outputDir)) {
      fs.rmSync(outputDir, { recursive: true, force: true });
    }
    ensureDirectoryExists(outputDir);

    // Generate TypeScript files for ValueSets inside the embedded package
    endPhase = startPhase('generate');
    const didGenerateValueSets = emitValueSetFiles(valueSets, outputDir, { deduplicateFilenames: true });
    if (!didGenerateValueSets) {
      cleanupStaleValueSetDir(outputDir);
    }
    // Build profile registries from BOTH main and dependency SDs so delegation can resolve names
    const { existingStructureDefinitions, profileIdToName, profileUrlToName, profileUrlToType } = buildProfileRegistries(allSDs, fhirInterfaceNames);

    // Register all local StructureDefinitions for resolution before HTTP fetches
    registerLocalStructureDefinitions(allSDs);

    // PackageManager already loaded and registered dependency SDs above —
    // no need to re-parse them via readStructureDefinitionsFromDependencies.

    for (const sd of structureDefinitions) {
      await processStructureDefinition(sd, { outputDir, fhirSourceHint: '', valueSetCodesMap, valueSets, existingStructureDefinitions, profileIdToName, profileUrlToName, profileUrlToType, flags });
    }
    // Process dependency SDs with noClasses to generate only validator/interface files (no Class = no parity testing)
    if (referencedDepSDs.length > 0) {
      const depFlags = { ...flags, noClasses: true };
      for (const sd of referencedDepSDs) {
        await processStructureDefinition(sd, { outputDir, fhirSourceHint: '', valueSetCodesMap, valueSets, existingStructureDefinitions, profileIdToName, profileUrlToName, profileUrlToType, flags: depFlags });
      }
    }
    endPhase(); // generate

    // Create package.json in generated folder
    const originalPackageJsonPath = path.join(extractedRoot, 'package', 'package.json');
    let packageName = path.basename(packageArchivePath, path.extname(packageArchivePath));
    let packageVersion = '1.0.0';

    let fhirMeta: Record<string, unknown> | undefined;
    if (fs.existsSync(originalPackageJsonPath)) {
      const originalPkg = JSON.parse(fs.readFileSync(originalPackageJsonPath, 'utf-8'));
      packageName = originalPkg.name || packageName;
      packageVersion = originalPkg.version || packageVersion;
      fhirMeta = {
        ig: originalPkg.name,
        version: originalPkg.version,
        ...(originalPkg.canonical && { canonical: originalPkg.canonical }),
        ...(originalPkg.fhirVersions && { fhirVersions: originalPkg.fhirVersions }),
        ...(flags?.txServer && { txServer: flags.txServer }),
        ...(flags?.displayLanguage && { displayLanguage: flags.displayLanguage }),
        ...(flags?.dicomweb && { dicomweb: true }),
        ...(flags?.noClient && { noClient: true }),
        ...(flags?.noClasses && { noClasses: true }),
        ...(flags?.schema && { schema: flags.schema }),
      };
    }

    const generatedExports: Record<string, { types: string; import: string }> = {
      '.': { types: './index.d.ts', import: './index.js' }
    };

    const generatedPackageJson: Record<string, unknown> = {
      name: `${packageName}-generated`,
      version: packageVersion,
      description: `Generated TypeScript interfaces for ${packageName}`,
      type: 'module',
      main: 'index.js',
      types: 'index.d.ts',
      exports: generatedExports,
      scripts: {},
      keywords: ['fhir', 'typescript', 'generated'],
      license: 'MIT',
      ...(fhirMeta && { fhir: fhirMeta }),
      // fhirpath is required at runtime by validators; keep as peer so host decides version
      peerDependencies: {
        'fhirpath': '^3.0.0 || ^4.0.0'
      },
      // Type definitions for FHIR are needed for the .d.ts files
      dependencies: {
        '@types/fhir': '^0.0.41'
      },
      devDependencies: {
        'babelfhir-ts': `^${GENERATOR_VERSION}`
      }
    };

    // When client is generated, add @babelfhir-ts/client-<version> as dependency (generated client extends base)
    if (!flags?.noClient) {
      (generatedPackageJson.dependencies as Record<string, string>)[`@babelfhir-ts/client-${versionSlug()}`] = '^0.2.0';
    }

    // When zod schemas are generated, add @babelfhir-ts/zod + zod peer dependency
    if (flags?.schema === 'zod') {
      (generatedPackageJson.dependencies as Record<string, string>)['@babelfhir-ts/zod'] = '^0.2.0';
      (generatedPackageJson.peerDependencies as Record<string, string>)['zod'] = '^4.0.0';
    }

    // When dicomweb is enabled, add @babelfhir-ts/dicomweb dependency
    if (flags?.dicomweb) {
      (generatedPackageJson.dependencies as Record<string, string>)['@babelfhir-ts/dicomweb'] = '^0.1.0';
    }

    copyFhirAmbientDeclaration(outputDir);

    // Generate index.ts that exports all interfaces
    logger.log('Generating index.ts exports...');
    await generateIndexFile(outputDir);

    // Generate FHIR client (unless --no-client flag)
    if (!flags?.noClient) {
      logger.log('Generating FHIR client...');

      // Load search parameters from base FHIR spec + IG for typed search param generation
      const searchParams = await loadSearchParameters(extractedRoot);

      const { generateClient } = await import('./emitters/client/clientGenerator.js');
      generateClient({
        outputDir,
        searchParams,
      });
      logger.log('FHIR client generated');
    }

    // Generate DICOMweb helpers (--dicomweb flag)
    if (flags?.dicomweb) {
      logger.log('Generating DICOMweb helpers...');
      const { generateDicomweb } = await import('./emitters/dicomweb/dicomwebGenerator.js');
      generateDicomweb({ outputDir });
    }

    // Only add subpath exports if their directories were actually created
    if (fs.existsSync(path.join(outputDir, 'fhir-client'))) {
      generatedExports['./fhir-client'] = { types: './fhir-client/index.d.ts', import: './fhir-client/index.js' };
    }
    if (fs.existsSync(path.join(outputDir, 'dicomweb'))) {
      generatedExports['./dicomweb'] = { types: './dicomweb/index.d.ts', import: './dicomweb/index.js' };
      generatedExports['./dicomweb/cornerstone'] = { types: './dicomweb/cornerstone.d.ts', import: './dicomweb/cornerstone.js' };
    }
    if (fs.existsSync(path.join(outputDir, 'valuesets'))) {
      generatedExports['./valuesets/*'] = { types: './valuesets/*.d.ts', import: './valuesets/*.js' };
    }

    const generatedPackageJsonPath = path.join(outputDir, 'package.json');
    fs.writeFileSync(generatedPackageJsonPath, JSON.stringify(generatedPackageJson, null, 2));
    logger.log(`Created package.json in generated folder: ${packageName}-generated@${packageVersion}`);

    // Install base zod type stubs when --schema zod is enabled (needed for tsc compilation)
    if (flags?.schema === 'zod') {
      const { installBaseZodTypes } = await import('./emitters/zod/zodStubInstaller.js');
      installBaseZodTypes(outputDir);
    }

    // Install fhirpath type stub so tsc can resolve validator imports
    const { installFhirpathStub, removeFhirpathStub } = await import('./emitters/validator/fhirpathStubInstaller.js');
    installFhirpathStub(outputDir);

    // Install minimal @types/node stub so tsc can resolve `import { createRequire } from 'module'`
    const nodeTypesDir = path.join(outputDir, 'node_modules', '@types', 'node');
    fs.mkdirSync(nodeTypesDir, { recursive: true });
    fs.writeFileSync(path.join(nodeTypesDir, 'index.d.ts'),
      `declare module 'module' {\n  export function createRequire(filename: string | URL): NodeRequire;\n}\n`);
    fs.writeFileSync(path.join(nodeTypesDir, 'package.json'),
      JSON.stringify({ name: '@types/node', version: '0.0.0-stub', types: 'index.d.ts' }));

    // Compile TypeScript to JavaScript
    endPhase = startPhase('compile');
    logger.log('Compiling TypeScript to JavaScript...');
    await compileTypeScriptToJS(outputDir);
    endPhase(); // compile
    // Remove fhirpath stub — the real package is a peer dependency
    removeFhirpathStub(outputDir);

    // Remove @types/node stub — only needed for compilation
    try { fs.rmSync(path.join(outputDir, 'node_modules', '@types'), { recursive: true, force: true }); } catch { /* ignore */ }

    // Remove base client type stubs — they were only needed for tsc to resolve
    // @babelfhir-ts/client-<version> imports during compilation. The real package is
    // installed by the consumer via npm.
    // Keep @babelfhir-ts/zod when zod schemas were generated (runtime needed for parity tests)
    const babelfhirDir = path.join(outputDir, 'node_modules', '@babelfhir-ts');
    if (fs.existsSync(babelfhirDir)) {
      for (const entry of fs.readdirSync(babelfhirDir)) {
        if (flags?.schema === 'zod' && entry === 'zod') continue;
        try { fs.rmSync(path.join(babelfhirDir, entry), { recursive: true, force: true }); } catch { /* ignore */ }
      }
      // Remove @babelfhir-ts dir if empty
      try { fs.rmdirSync(babelfhirDir); } catch { /* not empty — fine */ }
    }
    // Clean up empty node_modules if nothing else is in it
    const nodeModulesDir = path.join(outputDir, 'node_modules');
    try { fs.rmdirSync(nodeModulesDir); } catch { /* not empty or doesn't exist — fine */ }

    // Copy package.json to root of extractedRoot so it's at the tarball root
    const rootPackageJsonPath = path.join(extractedRoot, 'package.json');
    fs.copyFileSync(generatedPackageJsonPath, rootPackageJsonPath);
    logger.log('Copied package.json to tarball root');

    const finalArchive = outArchivePath || deriveOutputArchiveName(packageArchivePath);
    endPhase = startPhase('repack');
    await createPackageFromDir(extractedRoot, finalArchive);
    endPhase(); // repack

    // Write timing summary to output directory
    const timing = getTimingSummary();
    fs.writeFileSync(path.join(outputDir, 'generation-timing.json'), JSON.stringify(timing, null, 2));
    logger.log(formatTimingSummary(timing));

    return finalArchive;
  } finally {
    // Only clean up temp directories, not cached packages
    if (shouldCleanup) {
      try { fs.rmSync(extractedRoot, { recursive: true, force: true }); } catch (err) { log.debug(`Cleanup failed: ${(err as Error).message}`); }
    }
  }
}

/**
 * Generate TypeScript artefacts into a package but skip the intermediate archive
 * round-trip. Returns the generated directory path and a cleanup callback.
 * Used by the install command to avoid double tar operations.
 */
export async function generateIntoPackageDirect(
  packageArchivePath: string,
  flags?: GenerationFlags
): Promise<{ generatedDir: string; cleanup: () => void }> {
  initGenerationContext(flags, path.dirname(packageArchivePath));
  resetTimings();

  if (!packageArchivePath.endsWith('.tgz') && !packageArchivePath.endsWith('.zip')) throw new Error('Only .tgz or .zip supported.');
  let endPhase = startPhase('extract');
  const extractResult = await extractPackage(packageArchivePath);
  const extractedRoot = extractResult.path;
  endPhase();
  const shouldCleanup = !extractResult.isCached;

  // Auto-detect FHIR version from package when not explicitly set
  endPhase = startPhase('init');
  if (!flags?.fhirVersion) {
    const detected = detectFhirVersion(extractedRoot);
    await initVersionContext(detected ?? DEFAULT_FHIR_VERSION);
  } else {
    await initVersionContext(flags.fhirVersion);
  }
  const fhirInterfaceNames = ctx().interfaceNames;
  endPhase(); // init

  // Ensure dependency packages are downloaded BEFORE loading dependency SDs
  // (critical for CI cold cache — see generateIntoPackage for details)
  endPhase = startPhase('resolve');
  await ensureDependenciesDownloaded(extractedRoot);

  const { getPackageManager } = await import('./parser/packageManager.js');
  const packageManager = getPackageManager();
  packageManager.loadDependenciesFromExtractedPackage(extractedRoot);
  logger.log(`Loaded package dependencies (${packageManager.getTotalStructureDefinitionCount()} total SDs available)`);

  const structureDefinitions = readStructureDefinitionsFromDir(extractedRoot);

  // Collect dependency profiles for cross-package delegation
  const depPackageSDs = packageManager.getLoadedPackages().flatMap(p => p.structureDefinitions);
  const referencedDepSDs = collectReferencedDependencyProfiles(structureDefinitions, depPackageSDs);

  const valueSetCodesMap = readValueSetCodesWithDependencies(extractedRoot);
  let valueSets = readValueSetsFromDir(extractedRoot);
  logger.log(`Package contains ${structureDefinitions.length} StructureDefinitions (+ ${referencedDepSDs.length} delegation deps).`);
  logger.log(`Loaded ${Object.keys(valueSetCodesMap).length} ValueSet code mappings (including dependencies)`);
  endPhase(); // resolve

  const allSDs = [...structureDefinitions, ...referencedDepSDs];
  const bindingUrls = collectValueSetBindingUrls(allSDs);
  enrichValueSetsFromCodeMap(valueSets, valueSetCodesMap, bindingUrls);

  if (flags?.txServer) {
    valueSets = await expandValueSetsWithTx(valueSets, valueSetCodesMap, allSDs, flags.txServer, flags.displayLanguage);
  }

  const outputDir = path.join(extractedRoot, 'generated');
  if (fs.existsSync(outputDir)) {
    fs.rmSync(outputDir, { recursive: true, force: true });
  }
  ensureDirectoryExists(outputDir);

  endPhase = startPhase('generate');
  const didGenerateValueSets = emitValueSetFiles(valueSets, outputDir, { deduplicateFilenames: true });
  if (!didGenerateValueSets) cleanupStaleValueSetDir(outputDir);

  const { existingStructureDefinitions, profileIdToName, profileUrlToName, profileUrlToType } = buildProfileRegistries(allSDs, fhirInterfaceNames);
  registerLocalStructureDefinitions(allSDs);

  // PackageManager already loaded and registered dependency SDs above —
  // no need to re-parse them via readStructureDefinitionsFromDependencies.

  for (const sd of structureDefinitions) {
    await processStructureDefinition(sd, { outputDir, fhirSourceHint: '', valueSetCodesMap, valueSets, existingStructureDefinitions, profileIdToName, profileUrlToName, profileUrlToType, flags });
  }
  // Process dependency SDs with noClasses (validator-only, no parity testing)
  if (referencedDepSDs.length > 0) {
    const depFlags = { ...flags, noClasses: true };
    for (const sd of referencedDepSDs) {
      await processStructureDefinition(sd, { outputDir, fhirSourceHint: '', valueSetCodesMap, valueSets, existingStructureDefinitions, profileIdToName, profileUrlToName, profileUrlToType, flags: depFlags });
    }
  }
  endPhase(); // generate

  // Create package.json in generated folder
  const originalPackageJsonPath = path.join(extractedRoot, 'package', 'package.json');
  let packageName = path.basename(packageArchivePath, path.extname(packageArchivePath));
  let packageVersion = '1.0.0';
  let fhirMeta: Record<string, unknown> | undefined;
  if (fs.existsSync(originalPackageJsonPath)) {
    const originalPkg = JSON.parse(fs.readFileSync(originalPackageJsonPath, 'utf-8'));
    packageName = originalPkg.name || packageName;
    packageVersion = originalPkg.version || packageVersion;
    fhirMeta = {
      ig: originalPkg.name,
      version: originalPkg.version,
      ...(originalPkg.canonical && { canonical: originalPkg.canonical }),
      ...(originalPkg.fhirVersions && { fhirVersions: originalPkg.fhirVersions }),
      ...(flags?.txServer && { txServer: flags.txServer }),
      ...(flags?.displayLanguage && { displayLanguage: flags.displayLanguage }),
      ...(flags?.dicomweb && { dicomweb: true }),
      ...(flags?.noClient && { noClient: true }),
      ...(flags?.noClasses && { noClasses: true }),
      ...(flags?.schema && { schema: flags.schema }),
    };
  }

  const generatedExports: Record<string, { types: string; import: string }> = {
    '.': { types: './index.d.ts', import: './index.js' }
  };

  const generatedPackageJson: Record<string, unknown> = {
    name: `${packageName}-generated`,
    version: packageVersion,
    description: `Generated TypeScript interfaces for ${packageName}`,
    type: 'module',
    main: 'index.js',
    types: 'index.d.ts',
    exports: generatedExports,
    scripts: {},
    keywords: ['fhir', 'typescript', 'generated'],
    license: 'MIT',
    ...(fhirMeta && { fhir: fhirMeta }),
    peerDependencies: { 'fhirpath': '^3.0.0 || ^4.0.0' },
    dependencies: { '@types/fhir': '^0.0.41' },
    devDependencies: { 'babelfhir-ts': `^${GENERATOR_VERSION}` }
  };

  if (!flags?.noClient) {
    (generatedPackageJson.dependencies as Record<string, string>)[`@babelfhir-ts/client-${versionSlug()}`] = '^0.2.0';
  }
  if (flags?.schema === 'zod') {
    (generatedPackageJson.dependencies as Record<string, string>)['@babelfhir-ts/zod'] = '^0.2.0';
    (generatedPackageJson.peerDependencies as Record<string, string>)['zod'] = '^4.0.0';
  }

  // When dicomweb is enabled, add @babelfhir-ts/dicomweb dependency
  if (flags?.dicomweb) {
    (generatedPackageJson.dependencies as Record<string, string>)['@babelfhir-ts/dicomweb'] = '^0.1.0';
  }

  copyFhirAmbientDeclaration(outputDir);

  logger.log('Generating index.ts exports...');
  await generateIndexFile(outputDir);

  if (!flags?.noClient) {
    logger.log('Generating FHIR client...');
    const searchParams = await loadSearchParameters(extractedRoot);
    const { generateClient } = await import('./emitters/client/clientGenerator.js');
    generateClient({ outputDir, searchParams });
    logger.log('FHIR client generated');
  }

  // Generate DICOMweb helpers (--dicomweb flag)
  if (flags?.dicomweb) {
    logger.log('Generating DICOMweb helpers...');
    const { generateDicomweb } = await import('./emitters/dicomweb/dicomwebGenerator.js');
    generateDicomweb({ outputDir });
  }

  // Only add subpath exports if their directories were actually created
  if (fs.existsSync(path.join(outputDir, 'fhir-client'))) {
    generatedExports['./fhir-client'] = { types: './fhir-client/index.d.ts', import: './fhir-client/index.js' };
  }
  if (fs.existsSync(path.join(outputDir, 'dicomweb'))) {
    generatedExports['./dicomweb'] = { types: './dicomweb/index.d.ts', import: './dicomweb/index.js' };
    generatedExports['./dicomweb/cornerstone'] = { types: './dicomweb/cornerstone.d.ts', import: './dicomweb/cornerstone.js' };
  }
  if (fs.existsSync(path.join(outputDir, 'valuesets'))) {
    generatedExports['./valuesets/*'] = { types: './valuesets/*.d.ts', import: './valuesets/*.js' };
  }

  const generatedPackageJsonPath = path.join(outputDir, 'package.json');
  fs.writeFileSync(generatedPackageJsonPath, JSON.stringify(generatedPackageJson, null, 2));
  logger.log(`Created package.json in generated folder: ${packageName}-generated@${packageVersion}`);

  if (flags?.schema === 'zod') {
    const { installBaseZodTypes } = await import('./emitters/zod/zodStubInstaller.js');
    installBaseZodTypes(outputDir);
  }

  const { installFhirpathStub, removeFhirpathStub } = await import('./emitters/validator/fhirpathStubInstaller.js');
  installFhirpathStub(outputDir);

  const nodeTypesDir = path.join(outputDir, 'node_modules', '@types', 'node');
  fs.mkdirSync(nodeTypesDir, { recursive: true });
  fs.writeFileSync(path.join(nodeTypesDir, 'index.d.ts'),
    `declare module 'module' {\n  export function createRequire(filename: string | URL): NodeRequire;\n}\n`);
  fs.writeFileSync(path.join(nodeTypesDir, 'package.json'),
    JSON.stringify({ name: '@types/node', version: '0.0.0-stub', types: 'index.d.ts' }));

  endPhase = startPhase('compile');
  logger.log('Compiling TypeScript to JavaScript...');
  await compileTypeScriptToJS(outputDir);
  endPhase(); // compile

  removeFhirpathStub(outputDir);
  try { fs.rmSync(path.join(outputDir, 'node_modules', '@types'), { recursive: true, force: true }); } catch { /* ignore */ }

  const babelfhirDir = path.join(outputDir, 'node_modules', '@babelfhir-ts');
  if (fs.existsSync(babelfhirDir)) {
    for (const entry of fs.readdirSync(babelfhirDir)) {
      if (flags?.schema === 'zod' && entry === 'zod') continue;
      try { fs.rmSync(path.join(babelfhirDir, entry), { recursive: true, force: true }); } catch { /* ignore */ }
    }
    try { fs.rmdirSync(babelfhirDir); } catch { /* not empty — fine */ }
  }
  const nodeModulesDir = path.join(outputDir, 'node_modules');
  try { fs.rmdirSync(nodeModulesDir); } catch { /* not empty or doesn't exist — fine */ }

  // Write timing summary to output directory
  const timing = getTimingSummary();
  fs.writeFileSync(path.join(outputDir, 'generation-timing.json'), JSON.stringify(timing, null, 2));
  logger.log(formatTimingSummary(timing));

  return {
    generatedDir: outputDir,
    cleanup: () => {
      if (shouldCleanup) {
        try { fs.rmSync(extractedRoot, { recursive: true, force: true }); } catch { /* ignore */ }
      }
    }
  };
}

function deriveOutputArchiveName(input: string): string {
  const ext = input.endsWith('.tgz') ? '.tgz' : '.zip';
  return input.replace(ext, `.with-generated${ext}`);
}

/**
 * Batch mode: process every .tgz / .zip under inputDir and place results in outputDir.
 */
export async function generateForDirectory(inputDir: string, outputDir: string, flags?: GenerationFlags): Promise<void> {
  initGenerationContext(flags, outputDir);
  resetTimings();

  // Auto-detect FHIR version from directory contents when not explicitly set
  let endPhase = startPhase('init');
  if (!flags?.fhirVersion) {
    const detected = detectFhirVersion(inputDir);
    await initVersionContext(detected ?? DEFAULT_FHIR_VERSION);
  } else {
    await initVersionContext(flags.fhirVersion);
  }
  const fhirInterfaceNames = ctx().interfaceNames;
  endPhase(); // init

  if (!fs.existsSync(inputDir)) throw new Error(`Input directory not found: ${inputDir}`);
  if (!fs.existsSync(outputDir)) fs.mkdirSync(outputDir, { recursive: true });

  // Load ValueSets from the directory
  endPhase = startPhase('resolve');
  const valueSets = readValueSetsFromDir(inputDir);
  // Ensure dependency packages are downloaded before loading ValueSets
  await ensureDependenciesDownloaded(inputDir);

  // Register SDs from dependency packages so external profile resolution can find them
  const depSDs = readStructureDefinitionsFromDependencies(inputDir);
  registerLocalStructureDefinitions(depSDs);

  // Include dependency profiles referenced by main package type constraints for cross-package delegation
  // (applied later after localStructureDefinitions are collected from JSON files)

  const valueSetCodesMap = readValueSetCodesWithDependencies(inputDir);
  logger.log(`Loaded ${valueSets.size} ValueSets from ${inputDir} (${Array.from(valueSets.values()).filter(vs => vs.isSmall).length} suitable for union types)`);

  const entries = fs.readdirSync(inputDir);
  const archives = entries.filter(f => f.endsWith('.tgz') || f.endsWith('.zip'));
  const jsonFiles = entries.filter(f => f.endsWith('.json'));
  if (!archives.length && !jsonFiles.length) { log.warn(`No archives or StructureDefinition JSON in ${inputDir}`); return; }
  endPhase(); // resolve

  // Collect StructureDefinitions from JSON files, then build profile registries
  const localStructureDefinitions: StructureDefinition[] = [];
  for (const jf of jsonFiles) {
    try {
      const raw = JSON.parse(fs.readFileSync(path.join(inputDir, jf), 'utf-8')) as unknown;
      if (typeof raw === 'object' && raw !== null && (raw as {resourceType?:string}).resourceType === 'StructureDefinition') {
        localStructureDefinitions.push(raw as StructureDefinition);
      }
    } catch { /* ignore parse errors in pre-scan */ }
  }

  // Collect dependency profiles for cross-package delegation (validator-only)
  const referencedDepSDs = collectReferencedDependencyProfiles(localStructureDefinitions, depSDs);

  // Enrich ValueSets with codes resolved from CodeSystems (system-only compose.include)
  // Only create new entries for ValueSets actually referenced by the profiles' bindings
  const allLocalSDs = [...localStructureDefinitions, ...referencedDepSDs];
  const bindingUrls = collectValueSetBindingUrls(allLocalSDs);
  enrichValueSetsFromCodeMap(valueSets, valueSetCodesMap, bindingUrls);

  // Expand ValueSets from terminology server if configured
  if (flags?.txServer && allLocalSDs.length > 0) {
    const enrichedValueSets = await expandValueSetsWithTx(valueSets, valueSetCodesMap, allLocalSDs, flags.txServer, flags.displayLanguage);
    for (const [url, vs] of enrichedValueSets) {
      valueSets.set(url, vs);
    }
  }

  // Generate TypeScript files for ValueSets
  endPhase = startPhase('generate');
  if (!emitValueSetFiles(valueSets, outputDir)) {
    cleanupStaleValueSetDir(outputDir);
  }

  const { existingStructureDefinitions, profileIdToName, profileUrlToName, profileUrlToType } = buildProfileRegistries(allLocalSDs, fhirInterfaceNames);

  // Register all local StructureDefinitions for resolution before HTTP fetches
  registerLocalStructureDefinitions(allLocalSDs);

  for (const file of archives) {
    const fullPath = path.join(inputDir, file);
    logger.log(`Processing package: ${file}`);
    try {
      const outName = file.replace(/(\.tgz|\.zip)$/i, '.with-generated$1');
      const outArchive = path.join(outputDir, outName);
      await generateIntoPackage(fullPath, outArchive);
      logger.log(`→ Wrote ${outArchive}`);
    } catch (err) { log.error(`Failed processing ${file}:`, err); }
  }
  for (const jf of jsonFiles) {
    const full = path.join(inputDir, jf);
    try {
      const raw = JSON.parse(fs.readFileSync(full, 'utf-8')) as unknown;
      // Skip non-StructureDefinition resources (e.g., example Patient resources)
      if (typeof raw !== 'object' || raw === null || (raw as {resourceType?:string}).resourceType !== 'StructureDefinition') {
        continue;
      }
      await processStructureDefinition(raw as StructureDefinition, { outputDir, fhirSourceHint: full, valueSetCodesMap, valueSets, existingStructureDefinitions, profileIdToName, profileUrlToName, profileUrlToType, flags });
    } catch (err) { log.error(`Failed processing JSON ${jf}:`, err); }
  }
  // Process dependency SDs with noClasses (validator-only, no parity testing)
  if (referencedDepSDs.length > 0) {
    const depFlags = { ...flags, noClasses: true };
    for (const sd of referencedDepSDs) {
      await processStructureDefinition(sd, { outputDir, fhirSourceHint: '', valueSetCodesMap, valueSets, existingStructureDefinitions, profileIdToName, profileUrlToName, profileUrlToType, flags: depFlags });
    }
  }

  // Generate index.ts that exports all interfaces
  logger.log('Generating index.ts exports...');
  await generateIndexFile(outputDir);

  // Copy fhir-<version>.d.ts ambient module declaration
  copyFhirAmbientDeclaration(outputDir);

  // Generate FHIR client (unless --no-client flag)
  if (!flags?.noClient) {
    logger.log('Generating FHIR client...');
    const searchParams = await loadSearchParameters(inputDir);
    const { generateClient } = await import('./emitters/client/clientGenerator.js');
    generateClient({
      outputDir,
      searchParams,
    });
    logger.log('FHIR client generated');
  }

  // Generate DICOMweb helpers (--dicomweb flag)
  if (flags?.dicomweb) {
    logger.log('Generating DICOMweb helpers...');
    const { generateDicomweb } = await import('./emitters/dicomweb/dicomwebGenerator.js');
    generateDicomweb({ outputDir });
  }
  endPhase(); // generate

  // Write timing summary to output directory
  const timing = getTimingSummary();
  fs.writeFileSync(path.join(outputDir, 'generation-timing.json'), JSON.stringify(timing, null, 2));
  logger.log(formatTimingSummary(timing));
}

export async function generateFromJsonFile(jsonFilePath: string, outputDir: string, flags?: GenerationFlags): Promise<void> {
  // Initialize FHIR version context
  await initVersionContext(flags?.fhirVersion ?? DEFAULT_FHIR_VERSION);

  // Initialize logger and clear local StructureDefinitions from any previous generation
  initGenerationContext(flags, outputDir);

  if (!fs.existsSync(jsonFilePath)) throw new Error(`File not found: ${jsonFilePath}`);
  const raw = JSON.parse(fs.readFileSync(jsonFilePath, 'utf-8')) as unknown;
  if (typeof raw !== 'object' || raw === null || (raw as {resourceType?:string}).resourceType !== 'StructureDefinition') throw new Error(`Not a StructureDefinition: ${jsonFilePath}`);
  ensureDirectoryExists(outputDir);
  await processStructureDefinition(raw as StructureDefinition, { outputDir, fhirSourceHint: jsonFilePath, flags });
}

/**
 * Generate TypeScript interfaces/classes from a single FHIR profile by canonical URL
 * @param profileUrl - Canonical URL of the profile (e.g., http://hl7.org/fhir/us/core/StructureDefinition/us-core-patient)
 * @param outputDir - Output directory for generated files
 * @param flags - Generation options
 */
export async function generateFromProfileUrl(profileUrl: string, outputDir: string, flags?: GenerationFlags): Promise<void> {
  // Initialize FHIR version context
  await initVersionContext(flags?.fhirVersion ?? DEFAULT_FHIR_VERSION);

  // Clear local StructureDefinitions from any previous generation
  clearLocalStructureDefinitions();

  log.info(`Fetching profile: ${profileUrl}`);

  // Load all cached packages to make profile resolution work
  const { getPackageManager } = await import('./parser/packageManager.js');
  const packageManager = getPackageManager();

  if (!packageManager.hasCachedPackages()) {
    throw new Error(`No packages found in cache (${getFhirPackagesCacheDir()}). Please run a full generation first to populate the cache.`);
  }

  const loadedPackages = packageManager.loadAllCachedPackages();
  log.info(`Loaded ${loadedPackages.length} packages from cache (${packageManager.getTotalStructureDefinitionCount()} StructureDefinitions)`);

  const sd = await fetchStructureDefinition(profileUrl);
  if (!sd) {
    throw new Error(`Profile not found: ${profileUrl}\nMake sure the package containing this profile is in the cache.`);
  }

  ensureDirectoryExists(outputDir);
  await processStructureDefinition(sd, { outputDir, fhirSourceHint: profileUrl, flags });
  log.success(`Generated artifacts for profile: ${sd.name || sd.id}`);
}