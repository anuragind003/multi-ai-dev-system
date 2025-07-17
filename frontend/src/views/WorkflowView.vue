<!-- /src/views/WorkflowView.vue -->
<template>
  <div class="bg-gradient-to-br from-slate-50 via-white to-blue-50 min-h-screen">
    <!-- Header Section -->
    <div class="relative isolate overflow-hidden rounded-2xl bg-gradient-to-br from-slate-900 via-purple-900 to-slate-900">
      <!-- Enhanced background elements -->
      <div class="absolute inset-0 hero-bg-pattern opacity-30"></div>
      <div class="mx-auto max-w-7xl px-6 lg:px-8 py-12 relative z-10">
        <div class="text-center">
          <h1 class="text-3xl font-bold tracking-tight bg-gradient-to-r from-white via-blue-100 to-purple-100 bg-clip-text text-transparent sm:text-4xl lg:text-5xl mb-4 leading-tight">
            System Workflow
          </h1>
          <p class="mt-4 text-base leading-7 text-gray-300 max-w-2xl mx-auto font-light">
            An interactive overview of the automated development process from requirements to deployment.
          </p>
        </div>
      </div>
      <!-- Animated gradient orbs (optional, for more creativity) -->
      <div class="absolute inset-x-0 -top-40 -z-10 transform-gpu overflow-hidden blur-3xl sm:-top-80" aria-hidden="true">
        <div class="relative left-[calc(50%-11rem)] aspect-[1/1] w-[36.125rem] -translate-x-1/2 rotate-[30deg] rounded-full bg-gradient-to-tr from-[#ff80b5] via-[#9089fc] to-[#ff80b5] opacity-40 sm:left-[calc(50%-30rem)] sm:w-[72.1875rem] animate-pulse"></div>
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
        <div class="bg-white/80 backdrop-blur-sm p-8 rounded-3xl shadow-xl border border-gray-100 relative">
          <h2 class="text-2xl font-bold tracking-tight text-gray-900 sm:text-3xl mb-8 text-center">
            Development Process Flow
          </h2>
          <!-- Animation Controls -->
          <div class="flex justify-center mb-4 space-x-3">
            <button @click="animateFlow" :disabled="isAnimating" class="px-4 py-2 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 transition-colors duration-200 flex items-center gap-2">
              <PlayIcon class="w-4 h-4" />
              Animate Flow
            </button>
            <button @click="resetDiagram" class="px-4 py-2 bg-gray-600 text-white rounded-lg hover:bg-gray-700 transition-colors duration-200 flex items-center gap-2">
              <ArrowPathIcon class="w-4 h-4" />
              Reset
            </button>
            <button v-if="isAnimating && !isPaused" @click="pauseAnimation" class="px-4 py-2 bg-yellow-500 text-white rounded-lg hover:bg-yellow-600 transition-colors duration-200 flex items-center gap-2">
              Pause
            </button>
            <button v-if="isAnimating && isPaused" @click="resumeAnimation" class="px-4 py-2 bg-green-500 text-white rounded-lg hover:bg-green-600 transition-colors duration-200 flex items-center gap-2">
              Resume
            </button>
            <button v-if="isAnimating" @click="skipStep" class="px-4 py-2 bg-pink-500 text-white rounded-lg hover:bg-pink-600 transition-colors duration-200 flex items-center gap-2">
              Skip Step
            </button>
            <button v-if="!isAnimating && progress === 100" @click="replayAnimation" class="px-4 py-2 bg-purple-600 text-white rounded-lg hover:bg-purple-700 transition-colors duration-200 flex items-center gap-2">
              Replay
            </button>
          </div>
          <!-- Progress Bar -->
          <div class="w-full h-3 bg-gray-200 rounded-full mb-6 overflow-hidden">
            <div class="h-full bg-indigo-500 transition-all duration-300" :style="{ width: progress + '%' }"></div>
          </div>
          
          <!-- Floating label for animation step -->
          <div v-if="isAnimating && currentAnimationStep" class="fixed z-50 left-1/2 top-24 -translate-x-1/2 bg-indigo-900 text-white px-6 py-4 rounded-2xl shadow-2xl text-center animate-fade-in">
            <h4 class="font-bold text-lg mb-1">{{ currentAnimationStep.title }}</h4>
            <p class="text-sm">{{ currentAnimationStep.description }}</p>
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
import confetti from 'canvas-confetti';

interface NodeAnimationStep {
  type: 'node';
  id: string;
}

interface EdgeAnimationStep {
  type: 'edge';
  from: string;
  to: string;
  label?: string | null;
}

const highlightedStep = ref<string | null>(null);
const tooltipInfo = ref<any>(null);
const isAnimating = ref(false);
const isMermaidReady = ref(false); // New flag
const currentAnimationStep = ref<{ title: string, description: string } | null>(null);
const isPaused = ref(false);
const animationIndex = ref(0);
const shouldReplay = ref(false);
const shouldSkip = ref(false);
const progress = ref(0);

// Define the animation sequence for the main flow
const animationSequence: (NodeAnimationStep | EdgeAnimationStep)[] = [
  { type: 'node', id: 'A' },
  { type: 'edge', from: 'A', to: 'B' },
  { type: 'node', id: 'B' },
  { type: 'edge', from: 'B', to: 'C' },
  { type: 'node', id: 'C' },
  { type: 'edge', from: 'C', to: 'D', label: '✅ Approved' },
  { type: 'node', id: 'D' },
  { type: 'edge', from: 'D', to: 'E' },
  { type: 'node', id: 'E' },
  { type: 'edge', from: 'E', to: 'F', label: '✅ Approved' },
  { type: 'node', id: 'F' },
  { type: 'edge', from: 'F', to: 'G' },
  { type: 'node', id: 'G' },
  { type: 'edge', from: 'G', to: 'H', label: '✅ Approved' },
  { type: 'node', id: 'H' },
  { type: 'edge', from: 'H', to: 'I' },
  { type: 'node', id: 'I' },
  { type: 'edge', from: 'I', to: 'J', label: '✅ Approved' },
  { type: 'node', id: 'J' },
  { type: 'edge', from: 'J', to: 'K' },
  { type: 'node', id: 'K' },
  { type: 'edge', from: 'K', to: 'L', label: 'Next Item' }, // Loop part
  { type: 'node', id: 'L' },
  { type: 'edge', from: 'L', to: 'N' },
  { type: 'node', id: 'N' },
  { type: 'edge', from: 'N', to: 'O', label: '✅ Approved' },
  { type: 'node', id: 'O' },
  { type: 'edge', from: 'O', to: 'K', label: '✅ Passed' }, // Loop back to K
  // Assuming loop completes, then K -> M
  { type: 'edge', from: 'K', to: 'M', label: 'All Items Done' },
  { type: 'node', id: 'M' },
  { type: 'edge', from: 'M', to: 'P' },
  { type: 'node', id: 'P' }
];

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
    ],
    mermaidNodeId: 'B' // Map to Mermaid node B
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
    ],
    mermaidNodeId: 'D' // Map to Mermaid node D
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
    ],
    mermaidNodeId: 'F' // Map to Mermaid node F
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
    ],
    mermaidNodeId: 'H' // Map to Mermaid node H
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
    ],
    mermaidNodeId: 'J' // Map to Mermaid node J (Start Code Generation)
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
    ],
    mermaidNodeId: 'N' // Map to Mermaid node N (Code Quality Check)
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
    ],
    mermaidNodeId: 'M' // Map to Mermaid node M (Finalize Workflow)
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
    ],
    mermaidNodeId: 'P' // Map to Mermaid node P (End: Deployed Code)
  }
]);

// --- Sound for animation steps ---
const playStepSound = () => {
  const ctx = new (window.AudioContext || (window as any).webkitAudioContext)();
  const oscillator = ctx.createOscillator();
  const gain = ctx.createGain();
  oscillator.type = 'triangle';
  oscillator.frequency.value = 660;
  gain.gain.value = 0.08;
  oscillator.connect(gain);
  gain.connect(ctx.destination);
  oscillator.start();
  oscillator.stop(ctx.currentTime + 0.15);
  oscillator.onended = () => ctx.close();
};

const vibrateStep = () => {
  if (navigator.vibrate) {
    navigator.vibrate(60);
  }
};

// --- Animate edge drawing ---
const animateEdgeDraw = (pathElement: SVGPathElement) => {
  const length = pathElement.getTotalLength();
  pathElement.style.transition = 'none';
  pathElement.style.strokeDasharray = String(length);
  pathElement.style.strokeDashoffset = String(length);
  // Force reflow
  void pathElement.getBoundingClientRect();
  pathElement.style.transition = 'stroke-dashoffset 0.8s cubic-bezier(0.4,0,0.2,1)';
  pathElement.style.strokeDashoffset = '0';
};

const highlightEdge = (fromNodeId: string, toNodeId: string, label: string | null = null) => {
  const diagramContainer = document.getElementById('mermaid-diagram');
  if (diagramContainer) {
    const edgeGroups = diagramContainer.querySelectorAll('g.edge');
    edgeGroups.forEach(edgeGroup => {
      const edgeTitleElement = edgeGroup.querySelector('title');
      if (edgeTitleElement) {
        const edgeTitle = edgeTitleElement.textContent;
        let isMatch = false;
        if (edgeTitle) {
          isMatch = edgeTitle.includes(fromNodeId) && edgeTitle.includes(toNodeId);
          if (label && isMatch) {
            isMatch = edgeTitle.includes(label);
          }
        }
        if (isMatch) {
          const pathElement = edgeGroup.querySelector('path.flowchart-link') as SVGPathElement;
          if (pathElement) {
            pathElement.classList.add('highlighted-edge');
            animateEdgeDraw(pathElement); // Animate drawing
          }
          const textElement = edgeGroup.querySelector('text');
          if (textElement) {
            textElement.classList.add('highlighted-edge-text');
          }
        }
      }
    });
  }
};

const clearEdgeHighlight = () => {
  const diagramContainer = document.getElementById('mermaid-diagram');
  if (diagramContainer) {
    const edges = diagramContainer.querySelectorAll('path.highlighted-edge');
    edges.forEach(edge => {
      edge.classList.remove('highlighted-edge');
    });
    const edgeTexts = diagramContainer.querySelectorAll('text.highlighted-edge-text');
    edgeTexts.forEach(text => {
      text.classList.remove('highlighted-edge-text');
    });
  }
};

const highlightStep = (stepId: string) => {
  highlightedStep.value = stepId;
  
  // Highlight corresponding diagram node
  const diagramContainer = document.getElementById('mermaid-diagram');
  if (diagramContainer) {
    // Remove existing highlights from nodes and edges
    const nodes = diagramContainer.querySelectorAll('.node.highlighted-node');
    nodes.forEach(node => {
      node.classList.remove('highlighted-node');
    });
    clearEdgeHighlight();
    
    const stepToHighlight = workflowSteps.value.find(step => step.id === stepId);

    if (stepToHighlight && stepToHighlight.mermaidNodeId) {
      // Debug: log all node elements and their attributes
      const allNodes = diagramContainer.querySelectorAll('.node');
      allNodes.forEach((node: any) => {
        console.log('Mermaid node:', node, 'data-id:', node.getAttribute('data-id'), 'id:', node.id, 'text:', node.textContent);
      });
      // Try data-id
      let mermaidNodeElement = diagramContainer.querySelector(`[data-id="${stepToHighlight.mermaidNodeId}"]`);
      // Fallback: try id
      if (!mermaidNodeElement) {
        mermaidNodeElement = diagramContainer.querySelector(`#${stepToHighlight.mermaidNodeId}`);
      }
      // Fallback: try textContent includes node id
      if (!mermaidNodeElement) {
        allNodes.forEach((node: any) => {
          if (node.textContent && node.textContent.includes(stepToHighlight.mermaidNodeId)) {
            mermaidNodeElement = node;
          }
        });
      }
      if (mermaidNodeElement) {
        mermaidNodeElement.classList.add('highlighted-node');
      } else {
          console.warn(`Mermaid node for id "${stepToHighlight.mermaidNodeId}" not found by data-id, id, or textContent.`);
      }
    }
  }
};

const clearHighlight = () => {
  highlightedStep.value = null;
  tooltipInfo.value = null;
  
  // Clear diagram highlights from both nodes and edges
  const diagramContainer = document.getElementById('mermaid-diagram');
  if (diagramContainer) {
    const nodes = diagramContainer.querySelectorAll('.node');
    nodes.forEach(node => {
      node.classList.remove('highlighted-node', 'pulse-anim');
    });
    clearEdgeHighlight();
  }
};

const waitOrPause = async (ms: number) => {
  let elapsed = 0;
  const interval = 50;
  while (elapsed < ms) {
    if (shouldReplay.value) break;
    if (shouldSkip.value) break;
    if (!isPaused.value) {
      await new Promise(resolve => setTimeout(resolve, interval));
      elapsed += interval;
    } else {
      await new Promise(resolve => setTimeout(resolve, 100));
    }
  }
};

const animateFlow = async () => {
  if (isAnimating.value) return;
  if (!isMermaidReady.value) return;
  isAnimating.value = true;
  shouldReplay.value = false;
  shouldSkip.value = false;
  animationIndex.value = 0;
  progress.value = 0;
  await new Promise(resolve => setTimeout(resolve, 300));
  for (let i = 0; i < animationSequence.length; i++) {
    if (shouldReplay.value) break;
    animationIndex.value = i;
    progress.value = Math.round((i / animationSequence.length) * 100);
    clearHighlight();
    playStepSound();
    vibrateStep();
    const item = animationSequence[i];
    if (item.type === 'node') {
      const step = workflowSteps.value.find(s => s.mermaidNodeId === item.id);
      if (step) {
        highlightedStep.value = step.id;
        currentAnimationStep.value = { title: step.title, description: step.description };
      } else {
        currentAnimationStep.value = null;
      }
      const diagramContainer = document.getElementById('mermaid-diagram');
      if (diagramContainer) {
        let mermaidNodeElement = diagramContainer.querySelector(`[data-id="${item.id}"]`);
        if (!mermaidNodeElement) {
          mermaidNodeElement = diagramContainer.querySelector(`#${item.id}`);
        }
        if (!mermaidNodeElement) {
          const nodes = diagramContainer.querySelectorAll('.node');
          nodes.forEach((node: any) => {
            if (node.textContent && node.textContent.includes(item.id)) {
              mermaidNodeElement = node;
            }
          });
        }
        if (mermaidNodeElement) {
          mermaidNodeElement.classList.add('highlighted-node', 'pulse-anim');
        }
      }
    } else if (item.type === 'edge') {
      highlightEdge(item.from, item.to, item.label);
      currentAnimationStep.value = null;
    }
    shouldSkip.value = false;
    await waitOrPause(1500);
  }
  clearHighlight();
  currentAnimationStep.value = null;
  isAnimating.value = false;
  progress.value = 100;
  // Confetti celebration
  confetti({
    particleCount: 120,
    spread: 80,
    origin: { y: 0.6 },
    zIndex: 9999
  });
};

const resetDiagram = () => {
  console.log('Reset button clicked.');
  clearHighlight();
  isAnimating.value = false;
};

// Animation controls
function pauseAnimation() { isPaused.value = true; }
function resumeAnimation() { isPaused.value = false; }
function skipStep() { shouldSkip.value = true; }
function replayAnimation() {
  isPaused.value = false;
  shouldReplay.value = true;
}

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
      console.log('Mermaid SVG rendered into container. InnerHTML:', diagramContainer.innerHTML);
      
      // Add event listeners to diagram nodes for interactivity
      setTimeout(() => {
        const svgElement = diagramContainer.querySelector('svg');
        console.log('SVG Element found in setTimeout:', svgElement);
        if (svgElement) {
          const nodes = svgElement.querySelectorAll('.node');
          console.log('Nodes found in setTimeout:', nodes.length, nodes);
          nodes.forEach((node) => {
            const mermaidNodeId = node.getAttribute('data-id');
            const step = workflowSteps.value.find(s => s.mermaidNodeId === mermaidNodeId);

            if (step) {
              node.addEventListener('mouseenter', (e: Event) => {
                const mouseEvent = e as MouseEvent;
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
            }
          });
        }
      }, 100);
      
      isMermaidReady.value = true; // Set flag to true after everything is set up

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
  transform: scale(1.08);
  transition: all 0.3s ease;
}

.pulse-anim {
  animation: pulse-highlight 1.2s infinite;
}

@keyframes pulse-highlight {
  0% { box-shadow: 0 0 0 0 rgba(59,130,246,0.7); }
  70% { box-shadow: 0 0 0 12px rgba(59,130,246,0.0); }
  100% { box-shadow: 0 0 0 0 rgba(59,130,246,0.0); }
}

.highlighted-edge {
  stroke: #ff7f00 !important; /* Orange color */
  stroke-width: 4px !important;
  transition: stroke 0.3s ease-in-out, stroke-width 0.3s ease-in-out;
}

.highlighted-edge-text {
  fill: #ff7f00 !important;
  font-weight: bold !important;
}

/* Floating label animation */
.animate-fade-in {
  animation: fadeIn 0.5s;
}
@keyframes fadeIn {
  from { opacity: 0; transform: translateY(-20px); }
  to { opacity: 1; transform: translateY(0); }
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
.group:hover .group-hover\\:scale-110 {
  transform: scale(1.1);
}

.group:hover .group-hover\\:text-indigo-900 {
  color: rgb(49 46 129);
}

/* HomeView hero background pattern for consistency */
.hero-bg-pattern {
  background-image: url("data:image/svg+xml,%3csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 60 60' width='60' height='60'%3e%3cg fill='none' fill-rule='evenodd'%3e%3cg fill='%239C92AC' fill-opacity='0.05'%3e%3ccircle cx='30' cy='30' r='4'/%3e%3c/g%3e%3c/g%3e%3c/svg%3e");
}
</style>
