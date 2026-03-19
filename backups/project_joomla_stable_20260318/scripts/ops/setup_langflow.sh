#!/bin/bash
# Setup Langflow with RAG Custom Components

echo "=== Langflow + RAG Integration Setup ==="
echo ""

# 1. Create components directory
echo "[1/4] Creating Langflow components directory..."
mkdir -p ~/.langflow/components

# 2. Copy custom component
echo "[2/4] Copying RAG custom component..."
cp langflow_components/rag_existing_db.py ~/.langflow/components/

echo "  ✓ Component copied to: ~/.langflow/components/rag_existing_db.py"

# 3. Verify installation
echo ""
echo "[3/4] Verifying installation..."
if [ -f ~/.langflow/components/rag_existing_db.py ]; then
    echo "  ✓ Component file exists"
else
    echo "  ✗ Component file not found"
    exit 1
fi

# 4. Show next steps
echo ""
echo "[4/4] Setup complete!"
echo ""
echo "====================================="
echo "Next Steps:"
echo "====================================="
echo ""
echo "1. Start Langflow:"
echo "   langflow run --host 0.0.0.0 --port 7860"
echo ""
echo "2. Open browser:"
echo "   http://localhost:7860"
echo ""
echo "3. Look for custom components:"
echo "   - 'Existing RAG Database'"
echo "   - 'Full RAG System'"
echo ""
echo "4. Create a simple flow:"
echo "   [Chat Input] → [Full RAG System] → [Chat Output]"
echo ""
echo "5. Configure Full RAG System:"
echo "   RAG System Root: $(pwd)"
echo ""
echo "====================================="
echo ""
echo "Troubleshooting:"
echo "- If components don't appear: restart Langflow"
echo "- Check logs: ~/.langflow/langflow.log"
echo "- Verify path: ls ~/.langflow/components/"
echo ""
