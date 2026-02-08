export const APP_TITLE = "Deep Research";
export const AGENT_NAME = import.meta.env.VITE_LLAMA_DEPLOY_DEPLOYMENT_NAME;

export const SESSIONS_TITLE = "Sessions";

if (!AGENT_NAME) {
  throw new Error(
    "VITE_LLAMA_DEPLOY_DEPLOYMENT_NAME is required. Start via `llamactl serve` or set the env var.",
  );
}
