// BrdFallbackData.js - Fallback BRD analysis data for when the real data isn't available
export const fallbackBrdData = {
  project_name: "Task List Application",
  project_summary:
    "A simple application for creating and tracking tasks. This is a fallback/sample BRD used when the real analysis is not available.",
  requirements: [
    {
      id: "FR1",
      title: "Create Task",
      description: "Allow users to create new tasks with descriptions.",
    },
    {
      id: "FR2",
      title: "List Tasks",
      description: "Display a list of all created tasks.",
    },
    {
      id: "FR3",
      title: "Delete Task",
      description: "Allow users to remove tasks from the list.",
    },
  ],
  constraints: ["Must be web-based", "Should be responsive for mobile devices"],
  quality_assessment: {
    completeness_score: 8,
    clarity_score: 9,
    consistency_score: 10,
    overall_quality_score: 9,
  },
};
