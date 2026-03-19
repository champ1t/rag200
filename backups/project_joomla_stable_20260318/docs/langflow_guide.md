# How to Run NT RAG in LangFlow

This guide explains how to integrate the existing NT RAG System (`ChatEngine`) into a **LangFlow** canvas using the Custom Component feature.

## Prerequisites

1. **Python Environment**: Ensure LangFlow is running in an environment where your project dependencies (from `requirements.txt`) are installed.
   - If using Docker, you may need to mount your project folder into the container.
2. **Project Path**: You need to know the **absolute path** to your project root (the folder containing `src/`, `data/`, and `configs/`).

## Step-by-step Integration

### 1. Create a Custom Component
1. Open your LangFlow project.
2. In the Sidebar, look for **Custom Components** (or search for "Custom").
3. Drag a **Custom Component** node onto the canvas.

### 2. Inject the Adapter Code
1. Click the **Code** icon (</>) on the Custom Component node.
2. Delete the default code.
3. Copy the entire content of `langflow_adapter.py` (located in your project root).
4. Paste it into the LangFlow code editor.
5. Click **Check & Save** (or "Build").

### 3. Configure the Node
Once compiled, the node will update with specific fields:

- **Input Query**: The text input (can be linked from a Chat Input node).
- **Project Root Path**: **IMPORTANT**. Set this to the absolute path of your project.
  - Example (Mac): `/Users/jakkapatmac/Documents/NT/RAG/rag_web`
  - Example (Docker): `/app/rag_web` (depending on your volume mount)
- **Config File (Relative)**: Default is `configs/config.yaml`. Leave as is unless you have a custom config.
- **Session ID**: Optional session string for context tracking.

### 4. Run the Flow
1. Connect a **Chat Input** to the `Input Query` handle.
2. Connect the output `Text` to a **Chat Output**.
3. Run the flow.

## Troubleshooting

- **ModuleNotFoundError**: This means the `Project Root Path` is incorrect. The script needs strict access to `src/` to import `ChatEngine`.
- **Config not found**: Ensure `configs/config.yaml` exists relative to the Project Root.
- **Loading Time**: The first request will take 5-10 seconds to load the Vector DB and Directory. Subsequent requests will be instant (cached).
