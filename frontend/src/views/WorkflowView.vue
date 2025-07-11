<!-- /src/views/WorkflowView.vue -->
<template>
  <div class="bg-gradient-to-br from-slate-50 via-white to-blue-50 min-h-screen">
    <!-- Header Section -->
    <div class="relative bg-slate-900">
      <div class="mx-auto max-w-7xl px-6 lg:px-8 py-12">
        <div class="text-center">
          <h1 class="text-3xl font-bold tracking-tight bg-gradient-to-r from-white via-blue-100 to-purple-100 bg-clip-text text-transparent sm:text-4xl lg:text-5xl mb-4 leading-tight">
            System Workflow
          </h1>
          <p class="mt-4 text-base leading-7 text-gray-300 max-w-2xl mx-auto font-light">
            An interactive overview of the automated development process from requirements to deployment.
          </p>
        </div>
      </div>
    </div>

    <!-- Interactive Workflow Section -->
    <div class="py-16 sm:py-20">
      <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <!-- Interactive Cards Grid -->
        <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6 mb-12">
          <div 
            v-for="(step, index) in workflowSteps" 
            :key="step.id"
            @mouseenter="highlightStep(step.id)"
            @mouseleave="clearHighlight"
            :class="[
              'group relative p-6 bg-white/80 backdrop-blur-sm rounded-2xl shadow-lg border transition-all duration-300 cursor-pointer',
              'hover:shadow-2xl hover:scale-105 hover:border-indigo-200',
              highlightedStep === step.id ? 'ring-2 ring-indigo-500 bg-indigo-50/50' : 'border-gray-200'
            ]"
          >
            <!-- Step Icon -->
            <div :class="[
              'w-12 h-12 rounded-full flex items-center justify-center mb-4 transition-all duration-300',
              step.color,
              'group-hover:scale-110'
            ]">
              <component :is="step.icon" class="w-6 h-6 text-white" />
            </div>

            <!-- Step Info -->
            <div class="space-y-2">
              <div class="flex items-center gap-2">
                <span class="text-xs font-semibold text-indigo-600 bg-indigo-100 px-2 py-1 rounded-full">
                  {{ step.phase }}
                </span>
                <span v-if="step.isHumanApproval" class="text-xs font-semibold text-pink-600 bg-pink-100 px-2 py-1 rounded-full">
                  Human Review
                </span>
              </div>
              <h3 class="text-lg font-bold text-gray-900 group-hover:text-indigo-900">
                {{ step.title }}
              </h3>
              <p class="text-sm text-gray-600 leading-relaxed">
                {{ step.description }}
              </p>
              
              <!-- Expandable Details -->
              <div v-if="highlightedStep === step.id" class="mt-4 p-4 bg-indigo-50 rounded-lg transition-all duration-300">
                <h4 class="font-semibold text-indigo-900 mb-2">What happens here:</h4>
                <ul class="text-sm text-indigo-800 space-y-1">
                  <li v-for="detail in step.details" :key="detail" class="flex items-start gap-2">
                    <span class="text-indigo-500 mt-0.5">•</span>
                    {{ detail }}
                  </li>
                </ul>
                <div v-if="step.duration" class="mt-3 flex items-center gap-2">
                  <ClockIcon class="w-4 h-4 text-indigo-600" />
                  <span class="text-sm text-indigo-700 font-medium">{{ step.duration }}</span>
                </div>
              </div>
            </div>
          </div>
        </div>

        <!-- Mermaid Diagram Section -->
        <div class="bg-white/80 backdrop-blur-sm p-8 rounded-3xl shadow-xl border border-gray-100">
          <h2 class="text-2xl font-bold tracking-tight text-gray-900 sm:text-3xl mb-8 text-center">
            Development Process Flow
          </h2>
          
          <!-- Interactive Controls -->
          <div class="flex justify-center mb-6 space-x-4">
            <button 
              @click="animateFlow"
              class="px-4 py-2 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 transition-colors duration-200 flex items-center gap-2"
            >
              <PlayIcon class="w-4 h-4" />
              Animate Flow
            </button>
            <button 
              @click="resetDiagram"
              class="px-4 py-2 bg-gray-600 text-white rounded-lg hover:bg-gray-700 transition-colors duration-200 flex items-center gap-2"
            >
              <ArrowPathIcon class="w-4 h-4" />
              Reset
            </button>
          </div>

          <!-- Mermaid Diagram Container -->
          <div id="mermaid-diagram" class="w-full h-full flex justify-center items-center min-h-[600px]">
            <p class="text-gray-500">Diagram loading...</p>
          </div>

          <!-- Tooltip for diagram hover -->
          <div 
            v-if="tooltipInfo"
            :style="{ left: tooltipInfo.x + 'px', top: tooltipInfo.y + 'px' }"
            class="fixed z-50 bg-gray-900 text-white p-3 rounded-lg shadow-lg max-w-sm pointer-events-none"
          >
            <h4 class="font-semibold mb-1">{{ tooltipInfo.title }}</h4>
            <p class="text-sm">{{ tooltipInfo.description }}</p>
          </div>
        </div>
      </div>
    </div>

    <!-- Technology Stack Section -->
    <div class="py-16 bg-white/50">
      <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div class="text-center mb-12">
          <h3 class="text-2xl font-bold tracking-tight text-gray-900 mb-4">Supported Technologies</h3>
          <p class="text-lg text-gray-600">Our AI agents are trained on modern technology stacks and best practices</p>
        </div>
        
        <div class="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-8">
          <div class="text-center group">
            <div class="bg-white rounded-2xl p-6 shadow-lg hover:shadow-xl transition-all duration-300 group-hover:scale-105">
              <div class="text-4xl mb-3">⚛️</div>
              <div class="text-sm font-medium text-gray-700">React</div>
            </div>
          </div>
          <div class="text-center group">
            <div class="bg-white rounded-2xl p-6 shadow-lg hover:shadow-xl transition-all duration-300 group-hover:scale-105">
              <div class="text-4xl mb-3">🌿</div>
              <div class="text-sm font-medium text-gray-700">Vue.js</div>
            </div>
          </div>
          <div class="text-center group">
            <div class="bg-white rounded-2xl p-6 shadow-lg hover:shadow-xl transition-all duration-300 group-hover:scale-105">
              <div class="text-4xl mb-3">🐍</div>
              <div class="text-sm font-medium text-gray-700">Python</div>
            </div>
          </div>
          <div class="text-center group">
            <div class="bg-white rounded-2xl p-6 shadow-lg hover:shadow-xl transition-all duration-300 group-hover:scale-105">
              <div class="text-4xl mb-3">🟢</div>
              <div class="text-sm font-medium text-gray-700">Node.js</div>
            </div>
          </div>
          <div class="text-center group">
            <div class="bg-white rounded-2xl p-6 shadow-lg hover:shadow-xl transition-all duration-300 group-hover:scale-105">
              <div class="text-4xl mb-3">🐘</div>
              <div class="text-sm font-medium text-gray-700">PostgreSQL</div>
            </div>
          </div>
          <div class="text-center group">
            <div class="bg-white rounded-2xl p-6 shadow-lg hover:shadow-xl transition-all duration-300 group-hover:scale-105">
              <div class="text-4xl mb-3">🐳</div>
              <div class="text-sm font-medium text-gray-700">Docker</div>
            </div>
          </div>
          <div class="text-center group">
            <div class="bg-white rounded-2xl p-6 shadow-lg hover:shadow-xl transition-all duration-300 group-hover:scale-105">
              <div class="text-4xl mb-3">☁️</div>
              <div class="text-sm font-medium text-gray-700">AWS</div>
            </div>
          </div>
          <div class="text-center group">
            <div class="bg-white rounded-2xl p-6 shadow-lg hover:shadow-xl transition-all duration-300 group-hover:scale-105">
              <div class="text-4xl mb-3">🔥</div>
              <div class="text-sm font-medium text-gray-700">Firebase</div>
            </div>
          </div>
          <div class="text-center group">
            <div class="bg-white rounded-2xl p-6 shadow-lg hover:shadow-xl transition-all duration-300 group-hover:scale-105">
              <div class="text-4xl mb-3">⚡</div>
              <div class="text-sm font-medium text-gray-700">FastAPI</div>
            </div>
          </div>
          <div class="text-center group">
            <div class="bg-white rounded-2xl p-6 shadow-lg hover:shadow-xl transition-all duration-300 group-hover:scale-105">
              <div class="text-4xl mb-3">🎯</div>
              <div class="text-sm font-medium text-gray-700">TypeScript</div>
            </div>
          </div>
          <div class="text-center group">
            <div class="bg-white rounded-2xl p-6 shadow-lg hover:shadow-xl transition-all duration-300 group-hover:scale-105">
              <div class="text-4xl mb-3">🍃</div>
              <div class="text-sm font-medium text-gray-700">MongoDB</div>
            </div>
          </div>
          <div class="text-center group">
            <div class="bg-white rounded-2xl p-6 shadow-lg hover:shadow-xl transition-all duration-300 group-hover:scale-105">
              <div class="text-4xl mb-3">🚀</div>
              <div class="text-sm font-medium text-gray-700">GraphQL</div>
            </div>
          </div>
        </div>
        
        <div class="text-center mt-12">
          <p class="text-gray-600">And many more technologies based on your project requirements</p>
        </div>
      </div>
    </div>

    <!-- Footer -->
    <AppFooter />
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue';
import AppFooter from "@/components/AppFooter.vue";
import mermaid from 'mermaid';
import { 
  DocumentTextIcon, 
  CpuChipIcon, 
  CogIcon, 
  DocumentDuplicateIcon,
  CodeBracketIcon,
  BeakerIcon,
  RocketLaunchIcon,
  CheckCircleIcon,
  ClockIcon,
  PlayIcon,
  ArrowPathIcon
} from '@heroicons/vue/24/outline';

const highlightedStep = ref<string | null>(null);
const tooltipInfo = ref<any>(null);
const isAnimating = ref(false);

// Define workflow steps with detailed information
const workflowSteps = ref([
  {
    id: 'brd-analysis',
    phase: 'Phase 1',
    title: 'BRD Analysis',
    description: 'AI analyzes your Business Requirements Document to understand project needs.',
    icon: DocumentTextIcon,
    color: 'bg-gradient-to-br from-blue-500 to-blue-600',
    isHumanApproval: true,
    duration: 'Est. 2-3 minutes',
    details: [
      'Natural language processing of requirements',
      'Extraction of functional and non-functional requirements',
      'Identification of key stakeholders and use cases',
      'Risk assessment and constraint analysis',
      'Generation of structured requirement specifications'
    ]
  },
  {
    id: 'tech-stack',
    phase: 'Phase 2',
    title: 'Tech Stack Recommendation',
    description: 'AI suggests optimal technology stack based on requirements and best practices.',
    icon: CpuChipIcon,
    color: 'bg-gradient-to-br from-purple-500 to-purple-600',
    isHumanApproval: true,
    duration: 'Est. 3-4 minutes',
    details: [
      'Analysis of project requirements and constraints',
      'Evaluation of scalability and performance needs',
      'Selection of frameworks, databases, and tools',
      'Consideration of team expertise and preferences',
      'Cost and maintenance factor analysis'
    ]
  },
  {
    id: 'system-design',
    phase: 'Phase 3',
    title: 'System Design',
    description: 'Creates comprehensive system architecture and design patterns.',
    icon: CogIcon,
    color: 'bg-gradient-to-br from-emerald-500 to-emerald-600',
    isHumanApproval: true,
    duration: 'Est. 5-7 minutes',
    details: [
      'High-level system architecture design',
      'Database schema and data flow planning',
      'API design and service integration',
      'Security and authentication strategies',
      'Scalability and deployment considerations'
    ]
  },
  {
    id: 'implementation-plan',
    phase: 'Phase 4',
    title: 'Implementation Planning',
    description: 'Generates detailed development plan with work items and dependencies.',
    icon: DocumentDuplicateIcon,
    color: 'bg-gradient-to-br from-orange-500 to-orange-600',
    isHumanApproval: true,
    duration: 'Est. 3-5 minutes',
    details: [
      'Breaking down features into manageable work items',
      'Dependency mapping and sequencing',
      'Time estimation and resource allocation',
      'Priority assignment and milestone planning',
      'Quality checkpoints and testing strategies'
    ]
  },
  {
    id: 'code-generation',
    phase: 'Phase 5',
    title: 'Code Generation',
    description: 'AI agents generate production-ready code following best practices.',
    icon: CodeBracketIcon,
    color: 'bg-gradient-to-br from-indigo-500 to-indigo-600',
    isHumanApproval: false,
    duration: 'Est. 10-30 minutes',
    details: [
      'Automated code generation for all layers',
      'Implementation of business logic and APIs',
      'Database migration and seed data creation',
      'Frontend component and page development',
      'Integration of third-party services and APIs'
    ]
  },
  {
    id: 'quality-assurance',
    phase: 'Phase 6',
    title: 'Quality Assurance',
    description: 'Automated testing and code quality validation with iterative improvements.',
    icon: BeakerIcon,
    color: 'bg-gradient-to-br from-pink-500 to-pink-600',
    isHumanApproval: false,
    duration: 'Est. 5-10 minutes',
    details: [
      'Static code analysis and linting',
      'Unit test generation and execution',
      'Integration test validation',
      'Security vulnerability scanning',
      'Performance and optimization checks'
    ]
  },
  {
    id: 'deployment',
    phase: 'Phase 7',
    title: 'Deployment Setup',
    description: 'Automated deployment configuration and infrastructure setup.',
    icon: RocketLaunchIcon,
    color: 'bg-gradient-to-br from-green-500 to-green-600',
    isHumanApproval: false,
    duration: 'Est. 3-5 minutes',
    details: [
      'Docker containerization setup',
      'CI/CD pipeline configuration',
      'Environment variable management',
      'Database deployment and migrations',
      'Monitoring and logging setup'
    ]
  },
  {
    id: 'completion',
    phase: 'Complete',
    title: 'Project Ready',
    description: 'Fully functional application ready for production deployment.',
    icon: CheckCircleIcon,
    color: 'bg-gradient-to-br from-emerald-600 to-green-600',
    isHumanApproval: false,
    duration: 'Ready to deploy!',
    details: [
      'Complete, tested, and documented codebase',
      'Production-ready deployment configuration',
      'Comprehensive documentation and README',
      'Performance optimized and secure',
      'Ready for team handover and maintenance'
    ]
  }
]);

const highlightStep = (stepId: string) => {
  highlightedStep.value = stepId;
  
  // Highlight corresponding diagram node
  const diagramContainer = document.getElementById('mermaid-diagram');
  if (diagramContainer) {
    // Remove existing highlights
    const nodes = diagramContainer.querySelectorAll('.node');
    nodes.forEach(node => {
      node.classList.remove('highlighted-node');
    });
    
    // Add highlight to matching node (basic implementation)
    // In a more advanced implementation, you'd map stepId to specific diagram nodes
  }
};

const clearHighlight = () => {
  highlightedStep.value = null;
  tooltipInfo.value = null;
  
  // Clear diagram highlights
  const diagramContainer = document.getElementById('mermaid-diagram');
  if (diagramContainer) {
    const nodes = diagramContainer.querySelectorAll('.highlighted-node');
    nodes.forEach(node => {
      node.classList.remove('highlighted-node');
    });
  }
};

const animateFlow = async () => {
  if (isAnimating.value) return;
  
  isAnimating.value = true;
  
  // Animate through each step
  for (let i = 0; i < workflowSteps.value.length; i++) {
    highlightedStep.value = workflowSteps.value[i].id;
    await new Promise(resolve => setTimeout(resolve, 1500));
  }
  
  clearHighlight();
  isAnimating.value = false;
};

const resetDiagram = () => {
  clearHighlight();
  isAnimating.value = false;
};

onMounted(async () => {
  mermaid.initialize({
    startOnLoad: true,
    theme: 'neutral',
    securityLevel: 'loose',
    fontFamily: 'inherit',
    flowchart: {
      htmlLabels: true,
      curve: 'basis'
    }
  });

  const diagramContainer = document.getElementById('mermaid-diagram');

  if (diagramContainer) {
    const mermaidDefinition = `
graph TD
    subgraph "User Interaction"
        A[📄 Start: Upload BRD] --> B{🔍 BRD Analysis}
    end

    subgraph "AI-Powered Planning"
        B --> C{👤 Human Approval: BRD Analysis}
        C -->|✅ Approved| D[⚙️ Tech Stack Recommendation]
        C -->|❌ Revise| B
        D --> E{👤 Human Approval: Tech Stack}
        E -->|✅ Approved| F[🏗️ System Design]
        E -->|❌ Revise| D
        F --> G{👤 Human Approval: System Design}
        G -->|✅ Approved| H[📋 Implementation Plan]
        G -->|❌ Revise| F
    end

    subgraph "Automated Implementation"
        H --> I{👤 Human Approval: Plan}
        I -->|✅ Approved| J[🚀 Start Code Generation]
        I -->|❌ Revise| H
        J --> K[🔄 Work Item Iterator]
        K -->|Next Item| L[💻 Code Generation Agent]
        K -->|All Items Done| M[🎯 Finalize Workflow]
        L --> N{🧪 Code Quality Check}
        N -->|✅ Approved| O[🔬 Run Tests]
        N -->|❌ Revise| L
        O -->|✅ Passed| K
        O -->|❌ Failed| L
    end

    subgraph "Completion"
        M --> P[🎉 End: Deployed Code]
    end

    classDef startEnd fill:#22c55e,stroke:#16a34a,stroke-width:3px,color:#fff
    classDef humanApproval fill:#f59e0b,stroke:#d97706,stroke-width:2px,color:#fff
    classDef process fill:#3b82f6,stroke:#2563eb,stroke-width:2px,color:#fff
    classDef automated fill:#8b5cf6,stroke:#7c3aed,stroke-width:2px,color:#fff

    class A,P startEnd
    class C,E,G,I humanApproval
    class B,D,F,H process
    class J,K,L,N,O,M automated
`;

    try {
      const { svg } = await mermaid.render('mermaid-graph', mermaidDefinition);
      diagramContainer.innerHTML = svg;
      
      // Add event listeners to diagram nodes for interactivity
      setTimeout(() => {
        const svgElement = diagramContainer.querySelector('svg');
        if (svgElement) {
          const nodes = svgElement.querySelectorAll('.node');
          nodes.forEach((node, index) => {
            node.addEventListener('mouseenter', (e: Event) => {
              const mouseEvent = e as MouseEvent;
              const step = workflowSteps.value[Math.min(index, workflowSteps.value.length - 1)];
              tooltipInfo.value = {
                x: mouseEvent.clientX + 10,
                y: mouseEvent.clientY - 10,
                title: step.title,
                description: step.description
              };
            });
            
            node.addEventListener('mouseleave', () => {
              tooltipInfo.value = null;
            });
            
            node.addEventListener('mousemove', (e: Event) => {
              const mouseEvent = e as MouseEvent;
              if (tooltipInfo.value) {
                tooltipInfo.value.x = mouseEvent.clientX + 10;
                tooltipInfo.value.y = mouseEvent.clientY - 10;
              }
            });
          });
        }
      }, 100);
      
    } catch (error) {
      console.error('Mermaid rendering failed:', error);
      diagramContainer.innerHTML = '<p class="text-red-500">Failed to render diagram.</p>';
    }
  }
});
</script>

<style scoped>
/* Enhanced styles for interactive elements */
#mermaid-diagram svg {
  max-width: 100%;
  height: auto;
}

.highlighted-node {
  filter: drop-shadow(0 0 10px rgba(59, 130, 246, 0.8));
  transform: scale(1.05);
  transition: all 0.3s ease;
}

/* Custom gradient backgrounds */
.bg-clip-text {
  -webkit-background-clip: text;
  background-clip: text;
}

/* Smooth transitions for all interactive elements */
.transition-all {
  transition-property: all;
  transition-timing-function: cubic-bezier(0.4, 0, 0.2, 1);
  transition-duration: 300ms;
}

/* Enhanced hover effects */
.group:hover .group-hover\:scale-110 {
  transform: scale(1.1);
}

.group:hover .group-hover\:text-indigo-900 {
  color: rgb(49 46 129);
}
</style> 