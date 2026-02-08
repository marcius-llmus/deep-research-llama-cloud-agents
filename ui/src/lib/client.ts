import {
  ApiClients,
  createWorkflowsClient,
  cloudApiClient,
} from "@llamaindex/ui";
import { AGENT_NAME } from "./config";

if (!AGENT_NAME) {
  throw new Error(
    "VITE_LLAMA_DEPLOY_DEPLOYMENT_NAME is required to run the UI (AGENT_NAME).",
  );
}

const platformToken = import.meta.env.VITE_LLAMA_CLOUD_API_KEY;
const apiBaseUrl = import.meta.env.VITE_LLAMA_CLOUD_BASE_URL;
const projectId = import.meta.env.VITE_LLAMA_DEPLOY_PROJECT_ID;

cloudApiClient.setConfig({
  ...(apiBaseUrl && { baseUrl: apiBaseUrl }),
  headers: {
    ...(platformToken && { authorization: `Bearer ${platformToken}` }),
    ...(projectId && { "Project-Id": projectId }),
  },
});

export function createBaseWorkflowClient(): ReturnType<
  typeof createWorkflowsClient
> {
  return createWorkflowsClient({
    baseUrl: `/deployments/${AGENT_NAME}`,
  });
}

export function createApiClients(): ApiClients {
  const workflowsClient = createBaseWorkflowClient();

  return {
    workflowsClient,
    cloudApiClient,
  } as ApiClients;
}
