<!-- /src/views/HomeView.vue -->
<template>
  <!-- Set a main background for the view -->
  <div class="bg-gradient-to-br from-slate-50 via-white to-blue-50 min-h-screen">
    <!-- Hero Section -->
    <div class="relative isolate overflow-hidden rounded-2xl bg-gradient-to-br from-slate-900 via-purple-900 to-slate-900">
      <!-- Enhanced background elements -->
      <div class="absolute inset-0 hero-bg-pattern opacity-30"></div>
      
      <!-- Animated gradient orbs -->
      <div class="absolute inset-x-0 -top-40 -z-10 transform-gpu overflow-hidden blur-3xl sm:-top-80" aria-hidden="true">
        <div class="relative left-[calc(50%-11rem)] aspect-[1/1] w-[36.125rem] -translate-x-1/2 rotate-[30deg] rounded-full bg-gradient-to-tr from-[#ff80b5] via-[#9089fc] to-[#ff80b5] opacity-40 sm:left-[calc(50%-30rem)] sm:w-[72.1875rem] animate-pulse"></div>
      </div>
      
      <div class="mx-auto max-w-7xl px-6 lg:px-8 py-4 sm:py-6 lg:py-8">
        <div class="mx-auto max-w-4xl text-center">
          <!-- Enhanced logo container -->
          <div class="mb-6 flex justify-center">
            <div class="group relative rounded-3xl bg-white/10 p-4 ring-1 ring-white/20 backdrop-blur-xl border border-white/10 shadow-2xl hover:bg-white/20 transition-all duration-500 hover:scale-105">
              <div class="absolute inset-0 rounded-3xl bg-gradient-to-r from-purple-400/20 to-pink-400/20 opacity-0 group-hover:opacity-100 transition-opacity duration-500"></div>
              <img class="relative h-20 w-auto rounded-2xl" src="@/assets/logo.svg" alt="Company Logo" />
            </div>
          </div>
          
          <!-- Enhanced heading with gradient text -->
          <h1 class="text-3xl font-bold tracking-tight bg-gradient-to-r from-white via-blue-100 to-purple-100 bg-clip-text text-transparent sm:text-4xl lg:text-5xl mb-4 leading-tight">
            From Business Requirements to Deployed Code
          </h1>
          
          <!-- Enhanced subtitle -->
          <p class="mt-4 text-base leading-7 text-gray-300 max-w-2xl mx-auto font-light">
            Our AI-powered development platform analyzes your needs, designs the architecture, and generates production-ready applications.
          </p>
          
          <!-- Enhanced CTA button -->
          <div class="mt-8 flex items-center justify-center gap-x-6">
            <router-link 
              to="/new-project" 
              class="group relative inline-flex items-center px-6 py-2 text-sm font-semibold text-white transition-all duration-300 bg-gradient-to-r from-indigo-500 to-purple-600 rounded-xl hover:from-indigo-600 hover:to-purple-700 hover:scale-105 shadow-xl hover:shadow-2xl focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:ring-offset-2 focus:ring-offset-gray-900"
            >
              <span class="relative z-10">Start New Project</span>
              <svg class="ml-2 h-4 w-4 transition-transform group-hover:translate-x-1" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M17 8l4 4m0 0l-4 4m4-4H3" />
              </svg>
            </router-link>
          </div>
        </div>
      </div>
      
      <!-- Enhanced bottom gradient -->
      <div class="absolute inset-x-0 top-[calc(100%-13rem)] -z-10 transform-gpu overflow-hidden blur-3xl sm:top-[calc(100%-30rem)]" aria-hidden="true">
        <div class="relative left-[calc(50%+3rem)] aspect-[1/1] w-[36.125rem] -translate-x-1/2 rounded-full bg-gradient-to-tr from-[#ff80b5] via-[#9089fc] to-[#ff80b5] opacity-30 sm:left-[calc(50%+36rem)] sm:w-[72.1875rem] animate-pulse animation-delay-1000"></div>
      </div>
    </div>

    <!-- Features Section -->
    <div class="pt-16 sm:pt-20 pb-24 sm:pb-32 relative">
      <!-- Background pattern -->
      <div class="absolute inset-0 bg-gradient-to-br from-blue-50/50 to-purple-50/50"></div>
      
      <div class="relative max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div class="text-center mb-20">
          <div class="inline-flex items-center px-4 py-2 rounded-full text-sm font-medium bg-indigo-100 text-indigo-800 mb-4">
            ✨ How It Works
          </div>
          <h2 class="text-3xl font-bold tracking-tight bg-gradient-to-r from-gray-900 via-indigo-900 to-purple-900 bg-clip-text text-transparent sm:text-4xl mb-6">
            From Idea to Production
          </h2>
          <p class="mt-4 max-w-3xl text-lg text-gray-600 mx-auto leading-relaxed">
            Our platform guides your project from concept to code with continuous human oversight and AI-powered intelligence.
          </p>
        </div>

        <div class="relative">
          <!-- Enhanced connecting line with gradient -->
          <div aria-hidden="true" class="hidden lg:block absolute top-1/2 left-16 right-16 h-1 bg-gradient-to-r from-indigo-200 via-purple-200 to-indigo-200 transform -translate-y-1/2 rounded-full"></div>
          
          <div class="relative grid grid-cols-1 gap-8 md:grid-cols-2 md:gap-8 lg:grid-cols-4 lg:gap-8">
            <!-- Step 1: Define & Upload -->
            <div class="group flex flex-col text-center bg-white/80 backdrop-blur-sm p-8 rounded-3xl shadow-xl border border-gray-100 hover:border-indigo-200 transition-all duration-500 h-full hover:shadow-2xl hover:scale-105 relative overflow-hidden">
              <!-- Gradient overlay on hover -->
              <div class="absolute inset-0 bg-gradient-to-br from-indigo-50/0 to-purple-50/0 group-hover:from-indigo-50/50 group-hover:to-purple-50/50 transition-all duration-500 rounded-3xl"></div>
              
              <div class="relative z-10">
                <div class="mx-auto flex h-20 w-20 items-center justify-center rounded-full bg-gradient-to-br from-indigo-500 to-indigo-600 text-white ring-8 ring-white shadow-lg mb-6 group-hover:shadow-xl transition-all duration-300 group-hover:scale-110">
                  <svg class="h-10 w-10" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor" aria-hidden="true">
                    <path stroke-linecap="round" stroke-linejoin="round" d="M3 16.5v2.25A2.25 2.25 0 0 0 5.25 21h13.5A2.25 2.25 0 0 0 21 18.75V16.5m-13.5-9L12 3m0 0 4.5 4.5M12 3v13.5" />
                  </svg>
                </div>
                <div class="flex-grow">
                  <div class="text-xs font-semibold text-indigo-600 mb-2">Step 1</div>
                  <h3 class="text-lg font-bold text-gray-900 mb-4">Define & Upload</h3>
                  <p class="text-sm text-gray-600 leading-relaxed">Start by providing your Business Requirements Document (BRD) to kick off the intelligent development process.</p>
                </div>
              </div>
            </div>

            <!-- Step 2: AI-Powered Planning -->
            <div class="group flex flex-col text-center bg-white/80 backdrop-blur-sm p-8 rounded-3xl shadow-xl border border-gray-100 hover:border-purple-200 transition-all duration-500 h-full hover:shadow-2xl hover:scale-105 relative overflow-hidden">
              <div class="absolute inset-0 bg-gradient-to-br from-purple-50/0 to-pink-50/0 group-hover:from-purple-50/50 group-hover:to-pink-50/50 transition-all duration-500 rounded-3xl"></div>
              
              <div class="relative z-10">
                <div class="mx-auto flex h-20 w-20 items-center justify-center rounded-full bg-gradient-to-br from-purple-500 to-purple-600 text-white ring-8 ring-white shadow-lg mb-6 group-hover:shadow-xl transition-all duration-300 group-hover:scale-110">
                  <svg class="h-10 w-10" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor" aria-hidden="true">
                    <path stroke-linecap="round" stroke-linejoin="round" d="M9.813 15.904 9 18.75l-.813-2.846a4.5 4.5 0 0 0-3.09-3.09L2.25 12l2.846-.813a4.5 4.5 0 0 0 3.09-3.09L9 5.25l.813 2.846a4.5 4.5 0 0 0 3.09 3.09L15.75 12l-2.846.813a4.5 4.5 0 0 0-3.09 3.09ZM18.259 8.715 18 9.75l-.259-1.035a3.375 3.375 0 0 0-2.455-2.456L14.25 6l1.036-.259a3.375 3.375 0 0 0 2.455-2.456L18 2.25l.259 1.035a3.375 3.375 0 0 0 2.456 2.456L21.75 6l-1.035.259a3.375 3.375 0 0 0-2.456 2.456Z" />
                  </svg>
                </div>
                <div class="flex-grow">
                  <div class="text-xs font-semibold text-purple-600 mb-2">Step 2</div>
                  <h3 class="text-lg font-bold text-gray-900 mb-4">AI-Powered Planning</h3>
                  <p class="text-sm text-gray-600 leading-relaxed">Our AI analyzes requirements, proposes optimal tech stacks, and designs scalable system architecture.</p>
                </div>
              </div>
            </div>
            
            <!-- Step 3: Review & Approve -->
            <div class="group flex flex-col text-center bg-white/80 backdrop-blur-sm p-8 rounded-3xl shadow-xl border border-gray-100 hover:border-emerald-200 transition-all duration-500 h-full hover:shadow-2xl hover:scale-105 relative overflow-hidden">
              <div class="absolute inset-0 bg-gradient-to-br from-emerald-50/0 to-teal-50/0 group-hover:from-emerald-50/50 group-hover:to-teal-50/50 transition-all duration-500 rounded-3xl"></div>
              
              <div class="relative z-10">
                <div class="mx-auto flex h-20 w-20 items-center justify-center rounded-full bg-gradient-to-br from-emerald-500 to-emerald-600 text-white ring-8 ring-white shadow-lg mb-6 group-hover:shadow-xl transition-all duration-300 group-hover:scale-110">
                  <svg class="h-10 w-10" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor" aria-hidden="true">
                    <path stroke-linecap="round" stroke-linejoin="round" d="M9 12.75 11.25 15 15 9.75M21 12c0 1.268-.63 2.39-1.593 3.068a3.745 3.745 0 0 1-1.043 3.296 3.745 3.745 0 0 1-3.296 1.043A3.745 3.745 0 0 1 12 21c-1.268 0-2.39-.63-3.068-1.593a3.746 3.746 0 0 1-3.296-1.043 3.745 3.745 0 0 1-1.043-3.296A3.745 3.745 0 0 1 3 12c0-1.268.63-2.39 1.593-3.068a3.745 3.745 0 0 1 1.043-3.296 3.746 3.746 0 0 1 3.296-1.043A3.746 3.746 0 0 1 12 3c1.268 0 2.39.63 3.068 1.593a3.746 3.746 0 0 1 3.296 1.043 3.746 3.746 0 0 1 1.043 3.296A3.745 3.745 0 0 1 21 12Z" />
                  </svg>
                </div>
                <div class="flex-grow">
                  <div class="text-xs font-semibold text-emerald-600 mb-2">Step 3</div>
                  <h3 class="text-lg font-bold text-gray-900 mb-4">Review & Approve</h3>
                  <p class="text-sm text-gray-600 leading-relaxed">You review and approve the AI's comprehensive plan at each stage, ensuring perfect alignment with your vision.</p>
                </div>
              </div>
            </div>
            
            <!-- Step 4: Generate & Deploy -->
            <div class="group flex flex-col text-center bg-white/80 backdrop-blur-sm p-8 rounded-3xl shadow-xl border border-gray-100 hover:border-orange-200 transition-all duration-500 h-full hover:shadow-2xl hover:scale-105 relative overflow-hidden">
              <div class="absolute inset-0 bg-gradient-to-br from-orange-50/0 to-red-50/0 group-hover:from-orange-50/50 group-hover:to-red-50/50 transition-all duration-500 rounded-3xl"></div>
              
              <div class="relative z-10">
                <div class="mx-auto flex h-20 w-20 items-center justify-center rounded-full bg-gradient-to-br from-orange-500 to-orange-600 text-white ring-8 ring-white shadow-lg mb-6 group-hover:shadow-xl transition-all duration-300 group-hover:scale-110">
                  <svg class="h-10 w-10" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor" aria-hidden="true">
                    <path stroke-linecap="round" stroke-linejoin="round" d="M17.25 6.75 22.5 12l-5.25 5.25m-10.5 0L1.5 12l5.25-5.25" />
                  </svg>
                </div>
                <div class="flex-grow">
                  <div class="text-xs font-semibold text-orange-600 mb-2">Step 4</div>
                  <h3 class="text-lg font-bold text-gray-900 mb-4">Generate & Deploy</h3>
                  <p class="text-sm text-gray-600 leading-relaxed">With your approval, the AI generates enterprise-grade, production-ready code and deployment assets.</p>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Enhanced CTA Section -->
    <div class="mt-20 sm:mt-24 lg:mt-32 relative isolate overflow-hidden rounded-2xl bg-gradient-to-br from-slate-900 via-purple-900 to-slate-900 mb-8">
      <!-- Background pattern -->
      <div class="absolute inset-0 cta-bg-pattern opacity-30"></div>
      
      <!-- Gradient overlay -->
      <div class="absolute inset-0 bg-gradient-to-r from-transparent via-purple-500/20 to-transparent"></div>
      
      <div class="relative max-w-4xl mx-auto px-4 py-20 sm:px-6 sm:py-24 lg:px-8 text-center">
        <h2 class="text-3xl font-bold text-white sm:text-4xl mb-6 leading-tight">
          Ready to transform your business requirements?
        </h2>
        <p class="mt-4 text-lg leading-8 text-indigo-100 max-w-2xl mx-auto">
          Get started with our AI-powered development platform today and experience the future of software development.
        </p>
        <div class="mt-10">
          <router-link
            to="/new-project"
            class="group relative inline-flex items-center px-6 py-3 text-base font-semibold text-indigo-600 transition-all duration-300 bg-white rounded-2xl hover:bg-gray-50 hover:scale-105 shadow-xl hover:shadow-2xl focus:outline-none focus:ring-2 focus:ring-white focus:ring-offset-2 focus:ring-offset-indigo-600"
          >
            <span class="relative z-10">Create New Project</span>
            <svg class="ml-3 h-5 w-5 transition-transform group-hover:translate-x-1" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M17 8l4 4m0 0l-4 4m4-4H3" />
            </svg>
          </router-link>
        </div>
      </div>
    </div>

    <!-- Footer -->
    <AppFooter />
  </div>
</template>

<script setup lang="ts">
import AppFooter from "@/components/AppFooter.vue";
</script>

<style scoped>
@keyframes float {
  0%, 100% { transform: translateY(0px) rotate(0deg); }
  50% { transform: translateY(-10px) rotate(5deg); }
}

.animate-float {
  animation: float 6s ease-in-out infinite;
}

.animation-delay-1000 {
  animation-delay: 1s;
}

.animation-delay-2000 {
  animation-delay: 2s;
}

/* Custom gradient text */
.bg-clip-text {
  -webkit-background-clip: text;
  background-clip: text;
}

/* Smooth scrolling */
html {
  scroll-behavior: smooth;
}

/* Enhanced hover effects */
.group:hover .group-hover\:scale-110 {
  transform: scale(1.1);
}

.group:hover .group-hover\:translate-x-1 {
  transform: translateX(0.25rem);
}

.hero-bg-pattern {
  background-image: url("data:image/svg+xml,%3csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 60 60' width='60' height='60'%3e%3cg fill='none' fill-rule='evenodd'%3e%3cg fill='%239C92AC' fill-opacity='0.05'%3e%3ccircle cx='30' cy='30' r='4'/%3e%3c/g%3e%3c/g%3e%3c/svg%3e");
}

.cta-bg-pattern {
  background-image: url("data:image/svg+xml,%3csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 60 60' width='60' height='60'%3e%3cg fill='none' fill-rule='evenodd'%3e%3cg fill='%23ffffff' fill-opacity='0.1'%3e%3ccircle cx='30' cy='30' r='2'/%3e%3c/g%3e%3c/g%3e%3c/svg%3e");
}
</style>
