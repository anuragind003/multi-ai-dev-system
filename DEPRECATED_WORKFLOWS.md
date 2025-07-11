# DEPRECATED WORKFLOW FILES

⚠️ **These workflow files are deprecated and should not be used** ⚠️

The following files contain problematic sync/async mixing and state propagation issues:

## 🚫 DEPRECATED FILES:

1. **`async_graph.py`** - Contains sync/async mixing issues
2. **`async_graph_simple.py`** - Attempted fix but still has routing problems  
3. **`async_graph_nodes.py`** - Complex async wrappers around sync functions
4. **`fixed_workflow.py`** - Mixed approach that doesn't fully solve the issues

## ✅ USE INSTEAD:

**`unified_workflow.py`** - Clean, pure async implementation with:
- No sync/async mixing
- Consistent state management  
- Simple routing logic
- No Command API complexity
- Reliable work item iteration

## 🔧 MIGRATION:

Replace any imports:
```python
# OLD (deprecated)
from async_graph import get_async_workflow
from fixed_workflow import get_fixed_workflow

# NEW (recommended)
from unified_workflow import get_unified_workflow
```

## 📋 ISSUES SOLVED:

The unified workflow eliminates:
- ❌ `NameError: name 'async_route_after_work_item_iterator' is not defined`
- ❌ State propagation timing issues
- ❌ Command API complexity
- ❌ Sync function called in async context warnings
- ❌ Work item routing failures

## 🎯 ARCHITECTURE:

The unified workflow uses a **pure async approach**:
- All nodes are async functions
- Consistent error handling
- Simple state management
- Reliable routing decisions
- No external dependencies on sync wrappers 