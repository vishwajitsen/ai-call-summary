# mcp_router.py
#
# Central MCP router that connects all tool modules (Epic, FHIR,
# Azure, email, CRM, customer lookup, authentication, etc.)
# into a unified callable interface.


class MCPRouter:
    """
    Very simple but powerful MCP-style router.

    Example:
        router.register("customer.lookup", customer.lookup)
        router.register("epic.oauth", epic.get_token)

        router.call("customer.lookup", phone="5551234567")
    """

    def __init__(self):
        # A dict mapping: method_name -> python function
        self.methods = {}

    # -------------------------------------------------------
    # Register a method
    # -------------------------------------------------------
    def register(self, name: str, func):
        """Register a callable under a method name."""
        if not callable(func):
            raise ValueError(f"MCPRouter: {name} must be callable")

        self.methods[name] = func

    # -------------------------------------------------------
    # Call method
    # -------------------------------------------------------
    def call(self, name: str, **kwargs):
        """Call a registered MCP method."""
        if name not in self.methods:
            raise ValueError(f"MCPRouter: '{name}' not found")

        return self.methods[name](**kwargs)

    # -------------------------------------------------------
    # List registered methods
    # -------------------------------------------------------
    def list_methods(self):
        """Return list of all MCP method names."""
        return list(self.methods.keys())
