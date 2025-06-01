package com.ltfs.cdp.bre.drools;

import org.kie.api.KieBase;
import org.kie.api.KieServices;
import org.kie.api.builder.KieBuilder;
import org.kie.api.builder.KieFileSystem;
import org.kie.api.builder.KieModule;
import org.kie.api.builder.Message;
import org.kie.api.builder.Results;
import org.kie.api.runtime.KieContainer;
import org.kie.api.runtime.KieSession;
import org.springframework.beans.factory.config.ConfigurableBeanFactory;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.context.annotation.Scope;
import org.springframework.core.io.Resource;
import org.springframework.core.io.support.PathMatchingResourcePatternResolver;
import org.springframework.core.io.support.ResourcePatternResolver;
import org.kie.internal.io.ResourceFactory;

import java.io.IOException;
import java.util.Arrays;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

/**
 * Spring configuration for setting up the Drools KIE (Knowledge Is Everything) base and KIE session.
 * This class is responsible for loading DRL (Drools Rule Language) files, compiling them into a KieBase,
 * and providing a KieSession for rule execution within the Spring Boot application.
 */
@Configuration
public class DroolsConfig {

    private static final Logger log = LoggerFactory.getLogger(DroolsConfig.class);

    // Define the base path where Drools rule files (DRL) are located within the classpath.
    // For example, if DRLs are in src/main/resources/rules/, this should be "rules/".
    private static final String RULES_PATH = "rules/";

    /**
     * Provides the central interface for the KieServices.
     * This is the entry point for all Drools API calls, allowing access to KieContainers, KieBases, etc.
     *
     * @return An instance of KieServices.
     */
    @Bean
    public KieServices kieServices() {
        log.info("Initializing KieServices.");
        return KieServices.Factory.get();
    }

    /**
     * Creates and configures the KieFileSystem by loading all DRL files from the specified rules path.
     * The KieFileSystem acts as a virtual file system for Drools, where rule files are added before compilation.
     * It scans the classpath for DRL files and adds them to the KieFileSystem.
     *
     * @param kieServices The KieServices instance.
     * @return A configured KieFileSystem containing all discovered DRL files.
     * @throws IOException If there is an error reading the DRL files from the classpath.
     */
    @Bean
    public KieFileSystem kieFileSystem(KieServices kieServices) throws IOException {
        log.info("Scanning for DRL files in classpath: {}**/*.drl", RULES_PATH);
        KieFileSystem kieFileSystem = kieServices.newKieFileSystem();
        ResourcePatternResolver resourcePatternResolver = new PathMatchingResourcePatternResolver();
        // Use "classpath*:" to scan all JARs on the classpath, which is crucial in a Spring Boot fat JAR
        // or a multi-module project where rules might be in different modules.
        Resource[] drlResources = resourcePatternResolver.getResources("classpath*:" + RULES_PATH + "**/*.drl");

        if (drlResources.length == 0) {
            log.warn("No DRL files found in path: {}. Please ensure rules are placed correctly.", RULES_PATH);
        } else {
            log.info("Found {} DRL files: {}", drlResources.length, Arrays.toString(drlResources));
        }

        for (Resource file : drlResources) {
            // Determine the path within the KieFileSystem. This path should be relative to the
            // root of the KieModule, typically matching the classpath structure (e.g., "rules/dedupe/customer.drl").
            String resourceUrl = file.getURL().toExternalForm();
            String pathInKieFS;

            // Extract the part of the URL that represents the classpath resource path.
            // This handles different deployment scenarios (local development vs. JAR).
            int startIndex = -1;
            if (resourceUrl.contains("!/BOOT-INF/classes/")) { // For Spring Boot fat JARs
                startIndex = resourceUrl.indexOf("!/BOOT-INF/classes/") + "!/BOOT-INF/classes/".length();
            } else if (resourceUrl.contains("/target/classes/")) { // For local Maven/Gradle build output
                startIndex = resourceUrl.indexOf("/target/classes/") + "/target/classes/".length();
            } else if (resourceUrl.contains("/bin/")) { // For some IDE setups (e.g., Eclipse's /bin folder)
                startIndex = resourceUrl.indexOf("/bin/") + "/bin/".length();
            } else {
                // Fallback: If the resource path doesn't match common build output patterns,
                // try to find the RULES_PATH directly. This might be less robust.
                int rulesPathIndex = resourceUrl.indexOf(RULES_PATH);
                if (rulesPathIndex != -1) {
                    startIndex = rulesPathIndex;
                }
            }

            if (startIndex != -1) {
                pathInKieFS = resourceUrl.substring(startIndex);
            } else {
                log.error("Could not determine relative classpath path for DRL: {}. Skipping this file.", resourceUrl);
                continue;
            }

            // Ensure the path is clean (e.g., remove leading slashes if present from URL parsing)
            if (pathInKieFS.startsWith("/")) {
                pathInKieFS = pathInKieFS.substring(1);
            }

            // Add the resource to KieFileSystem using its input stream and the determined logical path.
            kieFileSystem.write(pathInKieFS, ResourceFactory.newInputStreamResource(file.getInputStream(), "UTF-8"));
            log.debug("Added DRL file to KieFileSystem: {}", pathInKieFS);
        }
        return kieFileSystem;
    }

    /**
     * Builds the KieContainer, which holds all the KIE Bases and KIE Sessions for a given KieModule.
     * This involves compiling the DRL files loaded into the KieFileSystem. If compilation errors occur,
     * an IllegalStateException is thrown to prevent the application from starting with invalid rules.
     *
     * @param kieServices The KieServices instance.
     * @param kieFileSystem The configured KieFileSystem with DRL files.
     * @return A compiled KieContainer.
     * @throws IllegalStateException if there are compilation errors in the Drools rule files.
     */
    @Bean
    public KieContainer kieContainer(KieServices kieServices, KieFileSystem kieFileSystem) {
        log.info("Building KieContainer from KieFileSystem.");
        final KieBuilder kieBuilder = kieServices.newKieBuilder(kieFileSystem);
        kieBuilder.buildAll(); // Compile all DRLs in the KieFileSystem

        Results results = kieBuilder.getResults();
        if (results.hasMessages(Message.Level.ERROR)) {
            // Log and throw an exception if there are compilation errors in DRL files.
            log.error("Drools rule compilation errors found:");
            for (Message message : results.getMessages()) {
                log.error("  - {}", message.getText());
            }
            throw new IllegalStateException("Drools rule compilation errors. See logs for details.");
        } else {
            log.info("Drools rules compiled successfully.");
        }

        // Get the KieModule and then the KieContainer from the compiled rules.
        KieModule kieModule = kieBuilder.getKieModule();
        return kieServices.newKieContainer(kieModule.getReleaseId());
    }

    /**
     * Provides the KieBase, which is a repository of all the application's knowledge definitions.
     * It contains the compiled rules and processes. KieBase is thread-safe and can be shared across multiple
     * KieSessions. It's typically a singleton bean.
     *
     * @param kieContainer The compiled KieContainer.
     * @return A KieBase instance.
     */
    @Bean
    public KieBase kieBase(KieContainer kieContainer) {
        log.info("Retrieving KieBase from KieContainer.");
        return kieContainer.getKieBase();
    }

    /**
     * Provides a new KieSession for each injection point.
     * A KieSession is the runtime component where rules are executed.
     * It is stateful by default, so it's crucial to create a new session for each independent rule execution
     * to avoid interference from previous executions or concurrent access issues.
     * The {@code @Scope(ConfigurableBeanFactory.SCOPE_PROTOTYPE)} annotation ensures a new instance
     * is created every time this bean is requested.
     *
     * @param kieBase The KieBase containing the compiled rules.
     * @return A new KieSession instance.
     */
    @Bean
    @Scope(ConfigurableBeanFactory.SCOPE_PROTOTYPE)
    public KieSession kieSession(KieBase kieBase) {
        log.debug("Creating new KieSession.");
        return kieBase.newKieSession();
    }
}