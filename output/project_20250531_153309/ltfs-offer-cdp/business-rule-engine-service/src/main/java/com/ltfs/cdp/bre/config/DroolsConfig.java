package com.ltfs.cdp.bre.config;

import org.kie.api.KieServices;
import org.kie.api.builder.KieBuilder;
import org.kie.api.builder.KieFileSystem;
import org.kie.api.builder.KieModule;
import org.kie.api.builder.Message;
import org.kie.api.runtime.KieContainer;
import org.kie.api.runtime.KieSession;
import org.kie.internal.io.ResourceFactory;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.core.io.Resource;
import org.springframework.core.io.support.PathMatchingResourcePatternResolver;
import org.springframework.core.io.support.ResourcePatternResolver;

import java.io.IOException;
import java.util.Arrays;

/**
 * Configuration class for Drools Business Rule Engine.
 * This class is responsible for setting up the KieServices, loading DRL (Drools Rule Language) files,
 * building the KieBase, and providing a KieSession for rule execution.
 *
 * The DRL files are expected to be located in the 'src/main/resources/rules/' directory.
 */
@Configuration
public class DroolsConfig {

    // Define the path where DRL files are located within the resources directory.
    // This pattern will match all .drl files in the 'rules' directory and its subdirectories.
    private static final String DRL_RULES_PATH = "rules/**/*.drl";

    /**
     * Provides the KieServices instance, which is the entry point for the Drools API.
     * KieServices is a singleton and provides access to all Drools components.
     *
     * @return The KieServices instance.
     */
    @Bean
    public KieServices kieServices() {
        return KieServices.Factory.get();
    }

    /**
     * Configures and provides the KieFileSystem, which is used to load DRL resources.
     * It scans the specified DRL_RULES_PATH for .drl files and adds them to the KieFileSystem.
     *
     * @param kieServices The KieServices instance.
     * @return The configured KieFileSystem.
     * @throws IOException If there is an error reading the DRL files from the classpath.
     * @throws IllegalStateException If no DRL files are found, indicating a potential configuration issue.
     */
    @Bean
    public KieFileSystem kieFileSystem(KieServices kieServices) throws IOException {
        KieFileSystem kieFileSystem = kieServices.newKieFileSystem();
        ResourcePatternResolver resourcePatternResolver = new PathMatchingResourcePatternResolver();
        // Resolve all DRL resources from the classpath based on the defined pattern.
        Resource[] drlResources = resourcePatternResolver.getResources("classpath*:" + DRL_RULES_PATH);

        if (drlResources.length == 0) {
            // Log a warning or throw an exception if no DRL files are found.
            // This might indicate a misconfiguration or missing rule files.
            throw new IllegalStateException("No DRL files found at path: " + DRL_RULES_PATH +
                    ". Please ensure your rule files are correctly placed.");
        }

        // Add each found DRL resource to the KieFileSystem.
        // The path within the KieFileSystem is derived from the resource's filename.
        Arrays.stream(drlResources).forEach(resource -> {
            try {
                kieFileSystem.write(ResourceFactory.newClassPathResource(
                        "rules/" + resource.getFilename(), // Assuming rules are directly under 'rules' folder
                        resource.getClassLoader()));
            } catch (IOException e) {
                // Log the error and rethrow as a runtime exception to fail fast during startup.
                throw new RuntimeException("Failed to load DRL resource: " + resource.getFilename(), e);
            }
        });

        return kieFileSystem;
    }

    /**
     * Builds the KieContainer from the KieFileSystem. The KieContainer holds the KieBase,
     * which is the compiled set of rules. This method also checks for any compilation errors
     * in the DRL files.
     *
     * @param kieServices The KieServices instance.
     * @param kieFileSystem The KieFileSystem containing the DRL resources.
     * @return The built KieContainer.
     * @throws RuntimeException If there are compilation errors in the DRL files.
     */
    @Bean
    public KieContainer kieContainer(KieServices kieServices, KieFileSystem kieFileSystem) {
        // Create a KieBuilder to build the KieModule from the KieFileSystem.
        KieBuilder kieBuilder = kieServices.newKieBuilder(kieFileSystem);
        kieBuilder.buildAll(); // Build all DRL files.

        // Check for any compilation errors in the DRL files.
        if (kieBuilder.getResults().hasMessages(Message.Level.ERROR)) {
            // Log all compilation errors and throw a runtime exception to prevent application startup
            // with faulty rules.
            StringBuilder errorMessage = new StringBuilder("Drools rule compilation errors:\n");
            kieBuilder.getResults().getMessages(Message.Level.ERROR).forEach(message ->
                    errorMessage.append(message.toString()).append("\n")
            );
            throw new RuntimeException(errorMessage.toString());
        }

        // Get the KieModule from the KieBuilder and then create a KieContainer.
        KieModule kieModule = kieBuilder.getKieModule();
        return kieServices.newKieContainer(kieModule.getReleaseId());
    }

    /**
     * Provides a KieSession from the KieContainer. The KieSession is the runtime component
     * where facts are inserted and rules are fired.
     *
     * @param kieContainer The KieContainer holding the compiled KieBase.
     * @return A new KieSession instance.
     */
    @Bean
    public KieSession kieSession(KieContainer kieContainer) {
        // Create a new KieSession. Each session is isolated and can be used for a single
        // rule execution context. For concurrent access, consider creating a new session
        // per request or using a pool of sessions.
        return kieContainer.newKieSession();
    }
}