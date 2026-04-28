# AI Operations Platform - UI Development Reference

**Version:** 1.0
**Date:** September 2025
**Purpose:** Comprehensive reference for UI development phase including API endpoints and template-driven UI generation system

---

## Table of Contents

1. [Part 1: API Endpoints Requiring UI Interfaces](#part-1-api-endpoints-requiring-ui-interfaces)
2. [Part 2: Template-Driven UI Generation System](#part-2-template-driven-ui-generation-system)
3. [User Query History & Context Management](#user-query-history--context-management)
4. [Future-Ready Architecture: Agents & Multi-Agent Systems](#future-ready-architecture-agents--multi-agent-systems)
5. [Database Schema Design](#database-schema-design)
6. [UI Page Architecture](#ui-page-architecture)
7. [Streamlit Best Practices Implementation](#streamlit-best-practices-implementation)
8. [Development Workflow](#development-workflow)

---

## Part 1: API Endpoints Requiring UI Interfaces

### 1.1 Authentication & User Management

#### **Login & Session Management**

```
POST /auth/token                    → Login Form
POST /auth/refresh                  → Auto-handled (background)
POST /auth/revoke                   → Logout functionality
GET /auth/validate                  → Auto-handled (session check)
```

#### **User Management (Admin Only)**

```
POST /auth/users                    → Create User Form
GET /auth/users                     → Users List/Table
GET /auth/users/{user_id}          → User Details View
PUT /auth/users/{user_id}          → Edit User Form
GET /auth/me                       → Current User Profile
```

**UI Requirements:**

- Login page with username/password
- User management dashboard (admin)
- User profile page
- Role-based access control

### 1.2 Core Orchestrator Operations

#### **Main Processing**

```
POST /api/v1/process               → Dynamic Use Case Interface
GET /                             → Dashboard/Welcome
GET /protected                    → Access verification
GET /health                       → System status widget
```

**UI Requirements:**

- Dynamic use case selection interface
- Real-time processing with streaming support
- System health monitoring dashboard

### 1.3 Document/Corpus Management

#### **Document Operations**

```
POST /api/v1/documents/            → Document Upload Interface
GET /api/v1/documents/             → Document Library/Browser
GET /api/v1/documents/{id}         → Document Details View
PATCH /api/v1/documents/{id}       → Document Edit Form
DELETE /api/v1/documents/{id}      → Delete confirmation dialog
GET /api/v1/documents/{id}/status  → Processing Status Monitor
GET /api/v1/documents/stats        → Document Statistics Dashboard
```

**UI Requirements:**

- Drag-and-drop file upload
- Document library with search/filter
- Metadata editing forms
- Processing status monitoring
- Statistics visualization

### 1.4 Query & Analytics

#### **Search Operations**

```
POST /api/v1/query/search          → Semantic Search Interface
POST /api/v1/query/ask             → RAG Question Interface
```

#### **Analytics & Monitoring**

```
GET /api/v1/analytics/documents/hot     → Hot Documents Widget
GET /api/v1/analytics/usage/stats       → Usage Analytics Dashboard
```

**UI Requirements:**

- Advanced search interface
- Q&A chat interface
- Analytics dashboards with charts
- Performance metrics visualization

### 1.5 Template & Use Case Management (New)

#### **Template Management**

```
POST /api/v1/admin/templates/                     → Template Creation Form
GET /api/v1/admin/templates/                      → Template Library
GET /api/v1/admin/templates/{id}                  → Template Editor
PUT /api/v1/admin/templates/{id}                  → Template Update
DELETE /api/v1/admin/templates/{id}               → Template Deletion
POST /api/v1/admin/templates/{id}/versions        → Version Creation
GET /api/v1/admin/templates/{id}/versions         → Version History
PUT /api/v1/admin/templates/{id}/versions/{v}/activate  → Version Activation
PUT /api/v1/admin/templates/{id}/versions/{v}/approve   → Version Approval
```

#### **Use Case Management**

```
POST /api/v1/admin/use-cases/                     → Use Case Creation Wizard
GET /api/v1/admin/use-cases/                      → Use Case Dashboard
GET /api/v1/admin/use-cases/{id}                  → Use Case Details
PUT /api/v1/admin/use-cases/{id}                  → Use Case Editor
PUT /api/v1/admin/use-cases/{id}/deploy           → Deployment Interface
GET /api/v1/admin/use-cases/active                → Active Use Cases List
GET /api/v1/admin/use-cases/{id}/config           → Use Case Configuration
```

**UI Requirements:**

- Template editor with syntax highlighting
- Version comparison interface
- Use case configuration wizard
- Deployment pipeline interface
- Approval workflow management

### 1.6 Query History & Context Management (New)

#### **Query History Operations**

```
GET /api/v1/users/{user_id}/query-history          → User Query History List
POST /api/v1/users/{user_id}/query-history         → Save Query to History
GET /api/v1/users/{user_id}/query-history/{id}     → Get Specific Query
PUT /api/v1/users/{user_id}/query-history/{id}     → Update Query (fork/modify)
DELETE /api/v1/users/{user_id}/query-history/{id}  → Delete Query from History
POST /api/v1/users/{user_id}/query-history/{id}/fork → Fork Query as New Base
```

#### **Context Thread Management**

```
GET /api/v1/users/{user_id}/threads                → User Thread List
POST /api/v1/users/{user_id}/threads               → Create New Thread
GET /api/v1/users/{user_id}/threads/{thread_id}    → Get Thread with Context
PUT /api/v1/users/{user_id}/threads/{thread_id}    → Update Thread (add message)
DELETE /api/v1/users/{user_id}/threads/{thread_id} → Delete Thread
POST /api/v1/users/{user_id}/threads/{thread_id}/compact → Compact Thread Context
GET /api/v1/users/{user_id}/threads/{thread_id}/stats   → Get Thread Stats (size, tokens)
```

#### **Security & Encryption Management**

```
GET /api/v1/admin/security/audit-log             → Security Audit Dashboard
GET /api/v1/admin/security/encryption-status     → Encryption Status Monitor
POST /api/v1/admin/security/rotate-keys          → Key Rotation Management
GET /api/v1/users/{user_id}/encryption-keys      → User Key Management
POST /api/v1/users/{user_id}/encryption-keys/rotate → Rotate User Keys
```

**UI Requirements:**

- Query history sidebar with search and filtering
- Thread-based conversation interface
- Context size indicator and management
- Query forking and modification interface
- Thread compaction tools
- Security audit dashboard
- Encryption key management interface
- Data classification indicators

---

## Part 2: Template-Driven UI Generation System

### 2.1 System Architecture

```mermaid
graph TB
    subgraph "Developer Workflow"
        A[Developer] --> B[Create Use Case Config]
        B --> C[Define Prompts]
        B --> D[Configure RAG Parameters]
        B --> E[Design UI Layout]
        B --> F[Set Output Format]
    end

    subgraph "Configuration Storage"
        G[(Use Case Configs)]
        H[(Template Versions)]
        I[(UI Components)]
    end

    subgraph "Runtime UI Generation"
        J[Use Case Selector]
        K[Dynamic UI Generator]
        L[Input Field Generator]
        M[Output Formatter]
        N[Validation Engine]
    end

    subgraph "End User Experience"
        O[Select Use Case]
        P[Fill Dynamic Form]
        Q[Execute & View Results]
    end

    B --> G
    C --> H
    E --> I

    G --> J
    J --> K
    K --> L
    K --> M
    K --> N

    J --> O
    L --> P
    M --> Q
    N --> P

    classDef developer fill:#e1f5fe
    classDef storage fill:#f3e5f5
    classDef runtime fill:#e8f5e8
    classDef user fill:#fff3e0

    class A,B,C,D,E,F developer
    class G,H,I storage
    class J,K,L,M,N runtime
    class O,P,Q user
```

### 2.2 Use Case Configuration Schema

```python
class UseCaseConfig(BaseModel):
    """Complete use case definition with UI generation capabilities"""

    # Metadata
    use_case_id: str
    name: str
    description: str
    category: str  # 'threat_hunting', 'incident_response', 'compliance'
    intent_type: RequestType
    version: str
    is_active: bool
    created_by: str
    approved_by: Optional[str] = None

    # Multi-type Prompt Configuration
    prompts: Dict[str, PromptConfig]  # 'system', 'user', 'tool'

    # RAG Configuration
    rag_config: RAGConfig

    # UI Generation Configuration
    ui_config: UIConfig

    # Output Configuration
    output_config: OutputConfig

    # Model & Parameter Overrides
    model_config: Optional[ModelConfig] = None

    # Validation Rules
    validation_rules: Optional[List[ValidationRule]] = None

    # Help & Documentation
    help_config: Optional[HelpConfig] = None

class UIConfig(BaseModel):
    """Comprehensive UI generation configuration"""

    # Layout Configuration
    layout_type: str  # 'single_column', 'two_column', 'tabbed', 'sidebar'
    page_title: str
    page_icon: Optional[str] = None

    # Input Configuration
    input_sections: List[InputSection]

    # Advanced Options
    advanced_options: Optional[AdvancedOptionsConfig] = None

    # Styling
    theme: Optional[str] = "default"
    custom_css: Optional[str] = None

class InputSection(BaseModel):
    """Grouped input fields with optional collapsible sections"""

    section_id: str
    section_title: str
    description: Optional[str] = None
    collapsible: bool = False
    expanded_by_default: bool = True
    fields: List[InputFieldConfig]

class InputFieldConfig(BaseModel):
    """Detailed input field configuration"""

    field_name: str
    field_type: str  # 'text_input', 'text_area', 'selectbox', 'multiselect', 'file_uploader', 'slider', 'date_input'
    label: str
    placeholder: Optional[str] = None
    required: bool = True
    default_value: Optional[Any] = None

    # Field-specific options
    options: Optional[List[str]] = None  # For selectbox/multiselect
    min_value: Optional[Union[int, float]] = None  # For slider/number_input
    max_value: Optional[Union[int, float]] = None
    step: Optional[Union[int, float]] = None

    # Validation
    validation_pattern: Optional[str] = None  # Regex
    validation_message: Optional[str] = None

    # UI Behavior
    help_text: Optional[str] = None
    disabled: bool = False
    width: Optional[str] = None  # 'full', 'half', 'third'

    # Conditional Display
    show_if: Optional[ConditionalRule] = None

class OutputConfig(BaseModel):
    """Comprehensive output configuration"""

    # Primary Display
    primary_display: DisplayConfig

    # Secondary Displays (tabs/expanders)
    secondary_displays: Optional[List[DisplayConfig]] = None

    # Download Options
    download_formats: Optional[List[DownloadFormat]] = None

    # Sharing Options
    sharing_enabled: bool = False

class DisplayConfig(BaseModel):
    """Individual display configuration"""

    display_id: str
    display_name: str
    display_type: str  # 'text', 'code', 'json', 'table', 'chart', 'metric', 'custom'

    # Content Processing
    content_path: str  # JSONPath to extract content from response
    format_template: Optional[str] = None  # Jinja2 template for formatting

    # Display Options
    language: Optional[str] = None  # For code display
    height: Optional[int] = None
    expandable: bool = False

    # Chart Configuration (if display_type == 'chart')
    chart_config: Optional[ChartConfig] = None

class ChartConfig(BaseModel):
    """Chart visualization configuration"""

    chart_type: str  # 'line', 'bar', 'area', 'scatter', 'pie'
    x_axis: str
    y_axis: Union[str, List[str]]
    color: Optional[str] = None
    title: Optional[str] = None
    height: int = 400
```

### 2.3 Dynamic UI Generator Implementation

```python
class DynamicUIGenerator:
    """Advanced UI generator with full Streamlit integration"""

    def __init__(self, use_case_config: UseCaseConfig):
        self.config = use_case_config
        self.session_state_key = f"uc_{use_case_config.use_case_id}"

    def render_use_case_ui(self):
        """Generate complete UI for the use case"""

        # Set page configuration
        st.set_page_config(
            page_title=self.config.ui_config.page_title,
            page_icon=self.config.ui_config.page_icon or "🛡️",
            layout="wide" if self.config.ui_config.layout_type == "two_column" else "centered"
        )

        # Apply custom CSS if provided
        if self.config.ui_config.custom_css:
            st.markdown(f"<style>{self.config.ui_config.custom_css}</style>", unsafe_allow_html=True)

        # Render header
        self._render_header()

        # Create layout based on configuration
        layout_containers = self._create_layout()

        # Generate input sections
        user_inputs = self._render_input_sections(layout_containers["input"])

        # Validation
        validation_errors = self._validate_inputs(user_inputs)

        # Execute button and processing
        if st.button(f"Execute {self.config.name}", type="primary", disabled=bool(validation_errors)):
            if not validation_errors:
                self._execute_and_render_results(user_inputs, layout_containers["output"])
            else:
                st.error("Please fix validation errors before proceeding")

        # Display validation errors
        for error in validation_errors:
            st.error(error)

    def _render_header(self):
        """Render use case header with description and help"""

        col1, col2 = st.columns([3, 1])

        with col1:
            st.title(self.config.name)
            st.markdown(self.config.description)

        with col2:
            if self.config.help_config:
                if st.button("ℹ️ Help"):
                    self._show_help_modal()

    def _create_layout(self) -> Dict[str, Any]:
        """Create layout containers based on configuration"""

        containers = {}

        if self.config.ui_config.layout_type == "two_column":
            col1, col2 = st.columns([1, 1])
            containers["input"] = col1
            containers["output"] = col2

        elif self.config.ui_config.layout_type == "sidebar":
            containers["input"] = st.sidebar
            containers["output"] = st.container()

        elif self.config.ui_config.layout_type == "tabbed":
            tab1, tab2 = st.tabs(["Input", "Results"])
            containers["input"] = tab1
            containers["output"] = tab2

        else:  # single_column
            containers["input"] = st.container()
            containers["output"] = st.container()

        return containers

    def _render_input_sections(self, container) -> Dict[str, Any]:
        """Render all input sections and fields"""

        all_inputs = {}

        with container:
            for section in self.config.ui_config.input_sections:
                section_inputs = self._render_input_section(section)
                all_inputs.update(section_inputs)

        return all_inputs

    def _render_input_section(self, section: InputSection) -> Dict[str, Any]:
        """Render a single input section"""

        section_inputs = {}

        if section.collapsible:
            with st.expander(section.section_title, expanded=section.expanded_by_default):
                if section.description:
                    st.markdown(section.description)
                section_inputs = self._render_fields(section.fields)
        else:
            st.subheader(section.section_title)
            if section.description:
                st.markdown(section.description)
            section_inputs = self._render_fields(section.fields)

        return section_inputs

    def _render_fields(self, fields: List[InputFieldConfig]) -> Dict[str, Any]:
        """Render individual input fields"""

        inputs = {}

        for field in fields:
            # Check conditional display
            if field.show_if and not self._evaluate_condition(field.show_if, inputs):
                continue

            # Create columns for width control
            if field.width == "half":
                col1, col2 = st.columns(2)
                field_container = col1
            elif field.width == "third":
                col1, col2, col3 = st.columns(3)
                field_container = col1
            else:
                field_container = st.container()

            with field_container:
                inputs[field.field_name] = self._render_single_field(field)

        return inputs

    def _render_single_field(self, field: InputFieldConfig) -> Any:
        """Render a single input field based on its configuration"""

        field_kwargs = {
            "label": field.label,
            "help": field.help_text,
            "disabled": field.disabled,
            "key": f"{self.session_state_key}_{field.field_name}"
        }

        if field.field_type == "text_input":
            return st.text_input(
                placeholder=field.placeholder,
                value=field.default_value or "",
                **field_kwargs
            )

        elif field.field_type == "text_area":
            return st.text_area(
                placeholder=field.placeholder,
                value=field.default_value or "",
                height=field.height or 100,
                **field_kwargs
            )

        elif field.field_type == "selectbox":
            return st.selectbox(
                options=field.options or [],
                index=self._get_default_index(field.options, field.default_value),
                **field_kwargs
            )

        elif field.field_type == "multiselect":
            return st.multiselect(
                options=field.options or [],
                default=field.default_value if isinstance(field.default_value, list) else [],
                **field_kwargs
            )

        elif field.field_type == "slider":
            return st.slider(
                min_value=field.min_value,
                max_value=field.max_value,
                value=field.default_value or field.min_value,
                step=field.step,
                **field_kwargs
            )

        elif field.field_type == "file_uploader":
            return st.file_uploader(
                accept_multiple_files=field.accept_multiple,
                type=field.accepted_types,
                **field_kwargs
            )

        elif field.field_type == "date_input":
            return st.date_input(
                value=field.default_value,
                **field_kwargs
            )

        # Add more field types as needed

    def _execute_and_render_results(self, user_inputs: Dict[str, Any], output_container):
        """Execute use case and render results"""

        with output_container:
            with st.spinner(f"Processing {self.config.name}..."):
                try:
                    # Execute the use case
                    result = self._call_orchestrator_api(user_inputs)

                    # Render primary display
                    self._render_display(self.config.output_config.primary_display, result)

                    # Render secondary displays in tabs
                    if self.config.output_config.secondary_displays:
                        tabs = st.tabs([d.display_name for d in self.config.output_config.secondary_displays])
                        for i, display in enumerate(self.config.output_config.secondary_displays):
                            with tabs[i]:
                                self._render_display(display, result)

                    # Render download options
                    if self.config.output_config.download_formats:
                        self._render_download_options(result)

                except Exception as e:
                    st.error(f"Error executing use case: {str(e)}")

    def _render_display(self, display_config: DisplayConfig, result: Dict):
        """Render a single display based on configuration"""

        # Extract content using JSONPath
        content = self._extract_content(result, display_config.content_path)

        # Apply format template if provided
        if display_config.format_template:
            content = self._apply_template(display_config.format_template, content, result)

        if display_config.display_type == "text":
            st.markdown(content)

        elif display_config.display_type == "code":
            st.code(content, language=display_config.language or "text")

        elif display_config.display_type == "json":
            st.json(content)

        elif display_config.display_type == "table":
            if isinstance(content, list):
                st.dataframe(content, height=display_config.height)
            else:
                st.error("Table display requires list data")

        elif display_config.display_type == "chart":
            if display_config.chart_config:
                self._render_chart(content, display_config.chart_config)
            else:
                st.error("Chart display requires chart configuration")

        elif display_config.display_type == "metric":
            if isinstance(content, dict) and "value" in content:
                st.metric(
                    label=content.get("label", "Metric"),
                    value=content["value"],
                    delta=content.get("delta")
                )
            else:
                st.error("Metric display requires dict with 'value' key")
```

---

## User Query History & Context Management

### 3.1 Query History System Architecture

The query history system enables users to build upon previous queries, creating an iterative workflow that improves over time. This MVP approach lays the foundation for more advanced context management and multi-turn conversations.

```mermaid
graph TB
    subgraph "Query History Flow"
        A[User Executes Query] --> B[Save to History]
        B --> C[Query History List]
        C --> D[Select Previous Query]
        D --> E[Fork & Modify]
        E --> F[Execute Modified Query]
        F --> B
    end

    subgraph "Context Thread Management"
        G[Create New Thread] --> H[Add Query to Thread]
        H --> I[Maintain Context Chain]
        I --> J[Context Size Monitor]
        J --> K{Size Limit?}
        K -->|Yes| L[Compact Context]
        K -->|No| H
        L --> H
    end

    subgraph "Future Agent Integration"
        M[Agent Orchestrator] -.-> N[Multi-Agent Workflow]
        N -.-> O[CrewAI Framework]
        O -.-> P[Tool Integration]
        P -.-> Q[MCP Protocols]
    end

    A --> G
    I --> M

    classDef current fill:#e8f5e8
    classDef future fill:#fff3e0,stroke-dasharray: 5 5

    class A,B,C,D,E,F,G,H,I,J,K,L current
    class M,N,O,P,Q future
```

### 3.2 Query History Data Models

```python
class QueryHistory(BaseModel):
    """User query history with forking capabilities"""

    id: str
    user_id: str
    thread_id: Optional[str] = None
    parent_query_id: Optional[str] = None  # For forked queries

    # Query Details
    use_case_id: str
    use_case_name: str
    query_title: str  # User-defined or auto-generated
    input_data: Dict[str, Any]

    # Execution Results
    output_data: Optional[Dict[str, Any]] = None
    execution_status: str  # 'success', 'failed', 'pending'
    execution_time_seconds: Optional[float] = None
    error_message: Optional[str] = None

    # Metadata
    created_at: datetime
    updated_at: datetime
    is_favorite: bool = False
    tags: List[str] = []
    notes: Optional[str] = None

    # Forking Metadata
    fork_count: int = 0
    is_forked: bool = False

class ContextThread(BaseModel):
    """Context thread for maintaining conversation state"""

    id: str
    user_id: str
    title: str
    description: Optional[str] = None

    # Context Management
    messages: List[ThreadMessage]
    context_size_tokens: int = 0
    max_context_tokens: int = 8000
    auto_compact: bool = True

    # Thread State
    is_active: bool = True
    created_at: datetime
    updated_at: datetime
    last_activity_at: datetime

    # Future: Agent Integration
    agent_config: Optional[Dict[str, Any]] = None  # Placeholder for agent settings
    multi_agent_workflow: Optional[str] = None     # Placeholder for workflow type

class ThreadMessage(BaseModel):
    """Individual message in a context thread"""

    id: str
    thread_id: str
    message_type: str  # 'user_input', 'system_response', 'agent_action'

    # Message Content
    content: str
    metadata: Dict[str, Any]
    token_count: int

    # Execution Context
    query_id: Optional[str] = None  # Link to query history
    use_case_id: Optional[str] = None

    # Timestamps
    created_at: datetime

    # Future: Agent Metadata
    agent_id: Optional[str] = None        # Placeholder for agent identification
    tool_calls: Optional[List[Dict]] = None  # Placeholder for tool usage

    # Security: Content encryption fields
    is_encrypted: bool = False            # Flag indicating if content is encrypted
    encryption_key_id: Optional[str] = None  # Reference to encryption key
```

### 3.3 Query History UI Components

#### **Query History Sidebar**

```python
class QueryHistoryWidget:
    """Streamlit widget for query history management"""

    def render_query_history_sidebar(self, user_id: str):
        """Render query history in sidebar"""

        with st.sidebar:
            st.subheader("📜 Query History")

            # Search and filter controls
            col1, col2 = st.columns(2)
            with col1:
                search_term = st.text_input("🔍", placeholder="Search queries...")
            with col2:
                filter_use_case = st.selectbox("Filter", ["All", "Recent", "Favorites"])

            # Query history list
            queries = self._load_query_history(user_id, search_term, filter_use_case)

            for query in queries:
                with st.container():
                    col1, col2, col3 = st.columns([3, 1, 1])

                    with col1:
                        if st.button(f"📝 {query.query_title}", key=f"query_{query.id}"):
                            self._load_query_into_form(query)

                    with col2:
                        if st.button("🍴", key=f"fork_{query.id}", help="Fork query"):
                            self._fork_query(query)

                    with col3:
                        if st.button("⭐" if query.is_favorite else "☆",
                                   key=f"fav_{query.id}", help="Toggle favorite"):
                            self._toggle_favorite(query)

                    # Show query preview
                    with st.expander(f"Preview - {query.use_case_name}"):
                        st.json(query.input_data)
                        if query.notes:
                            st.caption(f"Notes: {query.notes}")
```

#### **Context Thread Interface**

```python
class ContextThreadWidget:
    """Thread-based conversation interface"""

    def render_thread_interface(self, user_id: str):
        """Render thread-based conversation UI"""

        # Thread selector
        threads = self._load_user_threads(user_id)

        col1, col2 = st.columns([3, 1])
        with col1:
            selected_thread = st.selectbox(
                "💬 Conversation Thread",
                options=threads,
                format_func=lambda t: f"{t.title} ({len(t.messages)} messages)"
            )

        with col2:
            if st.button("➕ New Thread"):
                self._create_new_thread(user_id)

        if selected_thread:
            # Context size indicator
            self._render_context_indicator(selected_thread)

            # Thread messages
            self._render_thread_messages(selected_thread)

            # Thread management tools
            self._render_thread_tools(selected_thread)

    def _render_context_indicator(self, thread: ContextThread):
        """Render context size indicator"""

        usage_percent = (thread.context_size_tokens / thread.max_context_tokens) * 100

        col1, col2, col3 = st.columns([2, 1, 1])

        with col1:
            st.progress(usage_percent / 100)
            st.caption(f"Context: {thread.context_size_tokens}/{thread.max_context_tokens} tokens")

        with col2:
            if usage_percent > 80:
                if st.button("🗜️ Compact", help="Compress context"):
                    self._compact_thread_context(thread)

        with col3:
            if st.button("📊 Stats", help="Thread statistics"):
                self._show_thread_stats(thread)
```

### 3.4 Security & Encryption Requirements

#### **Data Security for Query History & Context**

All conversation history and context data must be secured according to enterprise security standards:

```python
class ConversationSecurity:
    """Security manager for conversation history and context data"""

    def __init__(self):
        # Encryption configuration
        self.encryption_algorithm = "AES-256-GCM"
        self.key_rotation_days = 90
        self.key_management_service = "Enterprise HSM"  # Hardware Security Module

        # Security policies
        self.encrypt_at_rest = True
        self.encrypt_in_transit = True
        self.require_field_level_encryption = True

    def encrypt_conversation_data(self, data: Dict[str, Any], user_id: str) -> Dict[str, Any]:
        """
        Encrypt sensitive conversation data before storage

        Fields requiring encryption:
        - Query content and parameters
        - System responses
        - User inputs
        - Context summaries
        - Error messages (may contain sensitive info)
        """

        # Get or create encryption key for user
        encryption_key = self._get_user_encryption_key(user_id)

        encrypted_data = {}
        sensitive_fields = [
            'content', 'input_data', 'output_data', 'query_title',
            'notes', 'error_message', 'context'
        ]

        for field, value in data.items():
            if field in sensitive_fields and value:
                encrypted_data[field] = self._encrypt_field(value, encryption_key)
                encrypted_data[f"{field}_encrypted"] = True
                encrypted_data["encryption_key_id"] = encryption_key.key_id
            else:
                encrypted_data[field] = value

        return encrypted_data

    def decrypt_conversation_data(self, encrypted_data: Dict[str, Any]) -> Dict[str, Any]:
        """Decrypt conversation data for display"""

        if not encrypted_data.get("encryption_key_id"):
            return encrypted_data  # Not encrypted

        encryption_key = self._get_encryption_key(encrypted_data["encryption_key_id"])
        decrypted_data = {}

        for field, value in encrypted_data.items():
            if field.endswith("_encrypted"):
                continue  # Skip encryption flags

            if encrypted_data.get(f"{field}_encrypted"):
                decrypted_data[field] = self._decrypt_field(value, encryption_key)
            else:
                decrypted_data[field] = value

        return decrypted_data

    def _encrypt_field(self, data: Any, encryption_key) -> str:
        """Encrypt individual field data"""
        # Implementation using enterprise-grade encryption libraries
        # Options for air-gapped environments:
        # - cryptography library (Python native)
        # - PyNaCl for high-level encryption
        # - Enterprise HSM integration via PKCS#11
        # - HashiCorp Vault for key management
        pass

    def _decrypt_field(self, encrypted_data: str, encryption_key) -> Any:
        """Decrypt individual field data"""
        # Implementation using same enterprise encryption libraries
        pass

    def _get_user_encryption_key(self, user_id: str):
        """Get or create encryption key for user"""
        # Implementation options for enterprise environments:
        # - HashiCorp Vault integration
        # - Enterprise HSM via PKCS#11 interface
        # - Local key derivation with master key in HSM
        # - File-based keystore with proper permissions
        pass

class SecureQueryHistoryManager:
    """Enhanced query history manager with encryption"""

    def __init__(self):
        self.security = ConversationSecurity()

    async def save_query_to_history(self, query_data: Dict[str, Any], user_id: str) -> str:
        """Save query to history with encryption"""

        # Encrypt sensitive data before storage
        encrypted_data = self.security.encrypt_conversation_data(query_data, user_id)

        # Add security metadata
        encrypted_data.update({
            "encrypted_at": datetime.now(timezone.utc),
            "encryption_version": "1.0",
            "data_classification": "confidential"
        })

        # Store in database
        return await self._store_encrypted_query(encrypted_data)

    async def load_query_from_history(self, query_id: str, user_id: str) -> Dict[str, Any]:
        """Load and decrypt query from history"""

        # Load encrypted data
        encrypted_data = await self._load_encrypted_query(query_id, user_id)

        # Verify user access
        if not self._verify_user_access(encrypted_data, user_id):
            raise SecurityError("Access denied to query history")

        # Decrypt data
        decrypted_data = self.security.decrypt_conversation_data(encrypted_data)

        # Log access for audit
        await self._log_data_access(query_id, user_id, "query_history_access")

        return decrypted_data
```

#### **Transport Security Requirements**

```python
class TransportSecurity:
    """Transport layer security for conversation data"""

    @staticmethod
    def configure_https_requirements():
        """Configure HTTPS requirements for all API endpoints"""
        return {
            "tls_version": "1.3",
            "cipher_suites": [
                "TLS_AES_256_GCM_SHA384",
                "TLS_CHACHA20_POLY1305_SHA256",
                "TLS_AES_128_GCM_SHA256"
            ],
            "certificate_validation": "strict",
            "hsts_enabled": True,
            "hsts_max_age": 31536000,  # 1 year
            "require_client_certificates": False  # Set to True for mutual TLS
        }

    @staticmethod
    def configure_api_security_headers():
        """Security headers for API responses"""
        return {
            "Strict-Transport-Security": "max-age=31536000; includeSubDomains",
            "X-Content-Type-Options": "nosniff",
            "X-Frame-Options": "DENY",
            "X-XSS-Protection": "1; mode=block",
            "Content-Security-Policy": "default-src 'self'",
            "Referrer-Policy": "strict-origin-when-cross-origin"
        }
```

#### **Database Security Configuration**

```sql
-- Enhanced security for conversation tables

-- Enable row-level security for query history
ALTER TABLE query_history ENABLE ROW LEVEL SECURITY;

-- Policy: Users can only access their own query history
CREATE POLICY query_history_user_isolation ON query_history
    FOR ALL TO authenticated_users
    USING (user_id = current_setting('app.current_user_id')::INTEGER);

-- Enable row-level security for context threads
ALTER TABLE context_threads ENABLE ROW LEVEL SECURITY;

-- Policy: Users can only access their own threads
CREATE POLICY context_threads_user_isolation ON context_threads
    FOR ALL TO authenticated_users
    USING (user_id = current_setting('app.current_user_id')::INTEGER);

-- Enable row-level security for thread messages
ALTER TABLE thread_messages ENABLE ROW LEVEL SECURITY;

-- Policy: Users can only access messages from their threads
CREATE POLICY thread_messages_user_isolation ON thread_messages
    FOR ALL TO authenticated_users
    USING (
        thread_id IN (
            SELECT thread_id FROM context_threads
            WHERE user_id = current_setting('app.current_user_id')::INTEGER
        )
    );

-- Create audit table for data access logging
CREATE TABLE conversation_audit_log (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id),
    action_type VARCHAR(50) NOT NULL,
    resource_type VARCHAR(50) NOT NULL,
    resource_id VARCHAR(255) NOT NULL,
    ip_address INET,
    user_agent TEXT,
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    success BOOLEAN DEFAULT true,
    error_message TEXT
);

-- Encryption key management table
CREATE TABLE encryption_keys (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    key_id VARCHAR(255) UNIQUE NOT NULL,
    user_id UUID REFERENCES users(id),
    key_type VARCHAR(50) DEFAULT 'conversation_data',
    algorithm VARCHAR(50) DEFAULT 'AES-256-GCM',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    expires_at TIMESTAMP WITH TIME ZONE,
    is_active BOOLEAN DEFAULT true,
    rotation_count INTEGER DEFAULT 0,
    hsm_key_reference VARCHAR(500), -- Enterprise HSM reference
    metadata JSON DEFAULT '{}'
);

-- Index for audit queries
CREATE INDEX idx_audit_user_time ON conversation_audit_log(user_id, timestamp);
CREATE INDEX idx_audit_resource ON conversation_audit_log(resource_type, resource_id);

-- Index for encryption keys
CREATE INDEX idx_encryption_keys_user ON encryption_keys(user_id, is_active);
CREATE INDEX idx_encryption_keys_active ON encryption_keys(key_id, is_active) WHERE is_active = true;
```

### 3.5 Context Management Algorithms

#### **Smart Context Compaction**

```python
class ContextManager:
    """Intelligent context management for threads"""

    def compact_context(self, thread: ContextThread, target_reduction: float = 0.3) -> ContextThread:
        """
        Compact thread context while preserving important information

        Strategy:
        1. Keep the most recent messages
        2. Preserve important system responses
        3. Summarize older conversation segments
        4. Maintain query-response pairs
        """

        if thread.context_size_tokens <= thread.max_context_tokens * 0.8:
            return thread  # No compaction needed

        # Identify important messages
        important_messages = self._identify_important_messages(thread.messages)
        recent_messages = thread.messages[-10:]  # Keep last 10 messages

        # Create compacted thread
        compacted_messages = []

        # Add summary of older messages
        older_messages = [msg for msg in thread.messages[:-10] if msg not in important_messages]
        if older_messages:
            summary = self._create_conversation_summary(older_messages)
            compacted_messages.append(ThreadMessage(
                id=f"summary_{uuid.uuid4()}",
                thread_id=thread.id,
                message_type="system_summary",
                content=summary,
                metadata={"compacted_messages": len(older_messages)},
                token_count=len(summary.split()) * 1.3,  # Rough token estimate
                created_at=datetime.now()
            ))

        # Add important messages
        compacted_messages.extend(important_messages)

        # Add recent messages
        compacted_messages.extend(recent_messages)

        # Update thread
        thread.messages = compacted_messages
        thread.context_size_tokens = sum(msg.token_count for msg in compacted_messages)

        return thread

    def _identify_important_messages(self, messages: List[ThreadMessage]) -> List[ThreadMessage]:
        """Identify messages that should be preserved during compaction"""

        important = []

        for msg in messages:
            # Keep messages with high engagement (favorites, notes)
            if msg.metadata.get("is_favorite") or msg.metadata.get("has_notes"):
                important.append(msg)

            # Keep error messages for debugging
            if msg.message_type == "system_response" and "error" in msg.content.lower():
                important.append(msg)

            # Keep successful query-response pairs with good results
            if (msg.message_type == "system_response" and
                msg.metadata.get("execution_status") == "success" and
                msg.metadata.get("user_rating", 0) >= 4):
                important.append(msg)

        return important
```

---

## Future-Ready Architecture: Agents & Multi-Agent Systems

### 4.1 Agent Integration Roadmap

This section outlines the future architecture for integrating AI agents, multi-agent workflows, and advanced tool usage into the AI Operations Platform (AIOP) platform. While not implemented in the initial phase, these stubs and markers ensure the system can evolve seamlessly.

```mermaid
graph TB
    subgraph "Current Architecture"
        A[User Input] --> B[Use Case Router]
        B --> C[Orchestrator]
        C --> D[LLM Client]
        D --> E[Response Formatter]
    end

    subgraph "Future Agent Layer"
        F[Agent Orchestrator] --> G[Agent Registry]
        G --> H[CrewAI Framework]
        H --> I[Individual Agents]
        I --> J[Tool Registry]
        J --> K[MCP Protocols]
    end

    subgraph "Agent Types (Future)"
        L[Research Agent]
        M[Analysis Agent]
        N[Rule Generation Agent]
        O[Validation Agent]
        P[Coordination Agent]
    end

    subgraph "Tool Ecosystem (Future)"
        Q[Security Tools]
        R[Data Sources]
        S[External APIs]
        T[Custom Scripts]
        U[MCP Connectors]
    end

    C --> F
    F --> L
    F --> M
    F --> N
    F --> O
    F --> P

    I --> Q
    I --> R
    I --> S
    I --> T
    I --> U

    classDef current fill:#e8f5e8
    classDef future fill:#fff3e0,stroke-dasharray: 5 5

    class A,B,C,D,E current
    class F,G,H,I,J,K,L,M,N,O,P,Q,R,S,T,U future
```

### 4.2 Agent Architecture Stubs

#### **Agent Registry & Management**

```python
# Future: Agent system stubs and markers

class AgentRegistry:
    """
    Future: Central registry for managing AI agents

    This will handle:
    - Agent discovery and registration
    - Capability matching
    - Load balancing
    - Health monitoring
    """

    def __init__(self):
        # TODO: Implement agent registry
        self.agents: Dict[str, 'BaseAgent'] = {}
        self.capabilities: Dict[str, List[str]] = {}

    async def register_agent(self, agent: 'BaseAgent') -> bool:
        """Register a new agent with the system"""
        # Stub for future implementation
        pass

    async def find_agents_by_capability(self, capability: str) -> List['BaseAgent']:
        """Find agents that can handle a specific capability"""
        # Stub for future implementation
        pass

    async def orchestrate_multi_agent_workflow(self, workflow_type: str, context: Dict) -> Any:
        """Orchestrate multiple agents for complex workflows"""
        # Future: Integration with CrewAI
        pass

class BaseAgent:
    """
    Future: Base class for all AI agents

    Agents will be specialized for different cybersecurity tasks:
    - ThreatHuntingAgent
    - IncidentResponseAgent
    - ComplianceAgent
    - ForensicsAgent
    """

    def __init__(self, agent_id: str, capabilities: List[str]):
        self.agent_id = agent_id
        self.capabilities = capabilities
        self.tools: List['BaseTool'] = []

        # Future: MCP integration
        self.mcp_client = None

    async def execute_task(self, task: 'AgentTask') -> 'AgentResult':
        """Execute a task assigned to this agent"""
        # Stub for future implementation
        pass

    async def collaborate_with_agent(self, other_agent: 'BaseAgent', context: Dict) -> Any:
        """Collaborate with another agent on a shared task"""
        # Future: Multi-agent collaboration
        pass

class AgentTask(BaseModel):
    """
    Future: Task definition for agent execution
    """
    task_id: str
    agent_id: str
    task_type: str
    input_data: Dict[str, Any]
    context: Dict[str, Any]
    priority: int = 1
    timeout_seconds: int = 300

    # Multi-agent coordination
    dependent_tasks: List[str] = []
    collaboration_required: bool = False

class AgentResult(BaseModel):
    """
    Future: Result from agent execution
    """
    task_id: str
    agent_id: str
    status: str  # 'success', 'failed', 'partial'
    result_data: Dict[str, Any]
    confidence_score: float
    execution_time_seconds: float

    # Tool usage tracking
    tools_used: List[str] = []
    external_calls: List[Dict] = []

    # Collaboration metadata
    collaborated_with: List[str] = []
    follow_up_tasks: List[str] = []
```

#### **CrewAI Integration Stubs**

```python
# Future: CrewAI framework integration

class CrewAIWorkflowManager:
    """
    Future: Integration with CrewAI for multi-agent workflows

    CrewAI will handle:
    - Agent coordination
    - Task delegation
    - Workflow orchestration
    - Result aggregation
    """

    def __init__(self):
        # TODO: Initialize CrewAI framework
        self.crews: Dict[str, 'Crew'] = {}
        self.workflow_templates: Dict[str, Dict] = {}

    async def create_crew_for_use_case(self, use_case: str, agents: List[BaseAgent]) -> 'Crew':
        """Create a crew of agents for a specific use case"""
        # Future: CrewAI crew creation
        pass

    async def execute_workflow(self, workflow_id: str, input_data: Dict) -> Dict:
        """Execute a multi-agent workflow"""
        # Future: Workflow execution with CrewAI
        pass

    def register_workflow_template(self, template_id: str, template: Dict):
        """Register a reusable workflow template"""
        # Future: Template-based workflow creation
        pass

# Future: Specialized cybersecurity agents

class ThreatHuntingAgent(BaseAgent):
    """
    Future: Specialized agent for threat hunting activities

    Capabilities:
    - IOC analysis
    - Behavioral analysis
    - Timeline construction
    - Evidence correlation
    """

    def __init__(self):
        super().__init__(
            agent_id="threat_hunter",
            capabilities=["ioc_analysis", "behavioral_analysis", "timeline_construction"]
        )

    async def hunt_for_threats(self, indicators: List[str], timeframe: str) -> Dict:
        """Hunt for threats based on indicators"""
        # Future: Threat hunting implementation
        pass

class IncidentResponseAgent(BaseAgent):
    """
    Future: Specialized agent for incident response

    Capabilities:
    - Incident classification
    - Response planning
    - Containment strategies
    - Recovery procedures
    """

    def __init__(self):
        super().__init__(
            agent_id="incident_responder",
            capabilities=["incident_classification", "response_planning", "containment"]
        )

    async def respond_to_incident(self, incident_data: Dict) -> Dict:
        """Generate incident response plan"""
        # Future: Incident response implementation
        pass
```

### 4.3 Tool Integration & MCP Protocol Stubs

#### **Tool Registry System**

```python
# Future: Advanced tool integration

class ToolRegistry:
    """
    Future: Registry for managing tools and MCP connections

    Will support:
    - Security tool integration (SIEM, EDR, etc.)
    - External API connections
    - Custom script execution
    - MCP protocol implementations
    """

    def __init__(self):
        self.tools: Dict[str, 'BaseTool'] = {}
        self.mcp_connections: Dict[str, 'MCPConnection'] = {}
        self.tool_categories: Dict[str, List[str]] = {}

    async def register_tool(self, tool: 'BaseTool') -> bool:
        """Register a new tool with the system"""
        # Future: Tool registration and validation
        pass

    async def execute_tool(self, tool_id: str, parameters: Dict) -> Any:
        """Execute a tool with given parameters"""
        # Future: Tool execution with error handling
        pass

    async def discover_mcp_tools(self, mcp_server: str) -> List[Dict]:
        """Discover available tools from MCP server"""
        # Future: MCP protocol implementation
        pass

class BaseTool:
    """
    Future: Base class for all tools
    """

    def __init__(self, tool_id: str, name: str, description: str):
        self.tool_id = tool_id
        self.name = name
        self.description = description
        self.parameters_schema: Dict = {}
        self.output_schema: Dict = {}

        # MCP integration
        self.mcp_compatible: bool = False
        self.mcp_server: Optional[str] = None

    async def execute(self, parameters: Dict) -> Any:
        """Execute the tool with given parameters"""
        raise NotImplementedError

    def validate_parameters(self, parameters: Dict) -> bool:
        """Validate input parameters against schema"""
        # Future: Parameter validation
        pass

# Future: Specific cybersecurity tools

class SIEMQueryTool(BaseTool):
    """Future: Tool for querying SIEM systems"""

    def __init__(self):
        super().__init__(
            tool_id="siem_query",
            name="SIEM Query Tool",
            description="Query SIEM systems for security events"
        )

    async def execute(self, parameters: Dict) -> Any:
        """Execute SIEM query"""
        # Future: SIEM integration
        pass

class ThreatIntelTool(BaseTool):
    """Future: Tool for threat intelligence lookups"""

    def __init__(self):
        super().__init__(
            tool_id="threat_intel",
            name="Threat Intelligence Tool",
            description="Lookup threat intelligence data"
        )

    async def execute(self, parameters: Dict) -> Any:
        """Lookup threat intelligence"""
        # Future: Threat intel API integration
        pass
```

### 4.4 Future Database Schema Extensions

```sql
-- Future: Agent and tool management tables

-- Agent registry
CREATE TABLE agents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    agent_id VARCHAR(255) UNIQUE NOT NULL,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    agent_type VARCHAR(100),
    capabilities JSON NOT NULL DEFAULT '[]',
    configuration JSON NOT NULL DEFAULT '{}',
    is_active BOOLEAN DEFAULT true,
    version VARCHAR(20) DEFAULT '1.0.0',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Agent tasks and executions
CREATE TABLE agent_tasks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    task_id VARCHAR(255) UNIQUE NOT NULL,
    agent_id VARCHAR(255) REFERENCES agents(agent_id),
    workflow_id VARCHAR(255),
    task_type VARCHAR(100),
    input_data JSON NOT NULL,
    context JSON DEFAULT '{}',
    status VARCHAR(20) DEFAULT 'pending',
    priority INTEGER DEFAULT 1,
    timeout_seconds INTEGER DEFAULT 300,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    started_at TIMESTAMP WITH TIME ZONE,
    completed_at TIMESTAMP WITH TIME ZONE
);

-- Tool registry
CREATE TABLE tools (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tool_id VARCHAR(255) UNIQUE NOT NULL,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    tool_type VARCHAR(100),
    parameters_schema JSON NOT NULL DEFAULT '{}',
    output_schema JSON NOT NULL DEFAULT '{}',
    is_mcp_compatible BOOLEAN DEFAULT false,
    mcp_server VARCHAR(255),
    is_active BOOLEAN DEFAULT true,
    version VARCHAR(20) DEFAULT '1.0.0',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Multi-agent workflows
CREATE TABLE agent_workflows (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    workflow_id VARCHAR(255) UNIQUE NOT NULL,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    workflow_type VARCHAR(100),
    agent_configuration JSON NOT NULL,
    execution_template JSON NOT NULL,
    is_active BOOLEAN DEFAULT true,
    created_by_user_id UUID REFERENCES users(id),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Tool executions
CREATE TABLE tool_executions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    execution_id VARCHAR(255) UNIQUE NOT NULL,
    tool_id VARCHAR(255) REFERENCES tools(tool_id),
    agent_task_id VARCHAR(255) REFERENCES agent_tasks(task_id),
    parameters JSON NOT NULL,
    result_data JSON,
    status VARCHAR(20) DEFAULT 'pending',
    execution_time_seconds FLOAT,
    error_message TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    completed_at TIMESTAMP WITH TIME ZONE
);

-- Indexes for future performance
CREATE INDEX idx_agent_tasks_status ON agent_tasks(status, created_at);
CREATE INDEX idx_tool_executions_tool ON tool_executions(tool_id, created_at);
CREATE INDEX idx_workflows_type ON agent_workflows(workflow_type, is_active);
```

### 4.5 Future UI Components for Agent Management

```python
# Future: Agent management UI components

class AgentManagementWidget:
    """Future: Streamlit widgets for agent management"""

    def render_agent_dashboard(self):
        """Render agent management dashboard"""

        st.header("🤖 Agent Management Dashboard")

        tab1, tab2, tab3, tab4 = st.tabs(["Active Agents", "Workflows", "Tools", "Monitoring"])

        with tab1:
            self._render_agent_registry()

        with tab2:
            self._render_workflow_designer()

        with tab3:
            self._render_tool_registry()

        with tab4:
            self._render_agent_monitoring()

    def _render_agent_registry(self):
        """Render agent registry interface"""
        # Future: Agent management UI
        st.info("🚧 Agent Registry - Coming Soon")
        st.markdown("""
        **Planned Features:**
        - Agent registration and configuration
        - Capability management
        - Agent health monitoring
        - Performance metrics
        """)

    def _render_workflow_designer(self):
        """Render multi-agent workflow designer"""
        # Future: Workflow design UI
        st.info("🚧 Workflow Designer - Coming Soon")
        st.markdown("""
        **Planned Features:**
        - Visual workflow builder
        - Agent coordination setup
        - Task dependency management
        - Workflow templates
        """)

    def _render_tool_registry(self):
        """Render tool registry interface"""
        # Future: Tool management UI
        st.info("🚧 Tool Registry - Coming Soon")
        st.markdown("""
        **Planned Features:**
        - Tool discovery and registration
        - MCP server connections
        - Tool testing interface
        - Usage analytics
        """)

class MultiAgentWorkflowWidget:
    """Future: Multi-agent workflow execution interface"""

    def render_workflow_execution(self, workflow_id: str):
        """Render workflow execution interface"""

        st.header(f"🔄 Multi-Agent Workflow: {workflow_id}")

        # Future: Real-time workflow monitoring
        st.info("🚧 Multi-Agent Workflow Execution - Coming Soon")

        col1, col2 = st.columns(2)

        with col1:
            st.subheader("Agent Status")
            # Future: Real-time agent status

        with col2:
            st.subheader("Task Progress")
            # Future: Task progress tracking
```

---

## Database Schema Design

### 3.1 Enhanced Schema Relationships

```mermaid
erDiagram
    users {
        int id PK
        string username UK
        string full_name
        string email UK
        string hashed_password
        string role
        boolean is_active
        json user_metadata
        timestamp created_at
        timestamp updated_at
        timestamp last_login
    }

    use_cases {
        int id PK
        string use_case_id UK
        string name
        string description
        string category
        string intent_type
        string version
        boolean is_active
        json config_json
        int created_by_user_id FK
        int approved_by_user_id FK
        timestamp deployed_at
        timestamp created_at
        timestamp updated_at
    }

    prompt_templates_v2 {
        int id PK
        string template_id
        string prompt_type
        int version_number
        int parent_template_id FK
        text template_content
        json variables
        boolean is_active_version
        int created_by_user_id FK
        int approved_by_user_id FK
        string deployment_status
        timestamp created_at
        timestamp updated_at
    }

    ui_components {
        int id PK
        string component_name UK
        string component_type
        json config_schema
        text render_template
        string version
        boolean is_active
        timestamp created_at
    }

    use_case_executions {
        int id PK
        string execution_id UK
        int use_case_id FK
        int user_id FK
        json input_data
        json output_data
        string status
        float execution_time_seconds
        string error_message
        timestamp started_at
        timestamp completed_at
    }

    template_approvals {
        int id PK
        int template_id FK
        int requested_by_user_id FK
        int approved_by_user_id FK
        string approval_status
        text approval_notes
        timestamp requested_at
        timestamp approved_at
    }

    use_case_deployments {
        int id PK
        int use_case_id FK
        string environment
        string deployment_status
        int deployed_by_user_id FK
        json deployment_config
        timestamp deployed_at
        timestamp rolled_back_at
    }

    query_history {
        int id PK
        string query_id UK
        int user_id FK
        string thread_id FK
        string parent_query_id FK
        string use_case_id
        string use_case_name
        string query_title
        json input_data
        json output_data
        string execution_status
        float execution_time_seconds
        string error_message
        timestamp created_at
        timestamp updated_at
        boolean is_favorite
        json tags
        text notes
        int fork_count
        boolean is_forked
    }

    context_threads {
        int id PK
        string thread_id UK
        int user_id FK
        string title
        text description
        int context_size_tokens
        int max_context_tokens
        boolean auto_compact
        boolean is_active
        timestamp created_at
        timestamp updated_at
        timestamp last_activity_at
        json agent_config
        string multi_agent_workflow
    }

    thread_messages {
        int id PK
        string message_id UK
        string thread_id FK
        string message_type
        text content
        json metadata
        int token_count
        string query_id FK
        string use_case_id
        timestamp created_at
        string agent_id
        json tool_calls
    }

    users ||--o{ use_cases : creates
    users ||--o{ prompt_templates_v2 : creates
    users ||--o{ use_case_executions : executes
    users ||--o{ template_approvals : approves
    users ||--o{ use_case_deployments : deploys
    users ||--o{ query_history : "has history"
    users ||--o{ context_threads : "owns threads"

    use_cases ||--o{ use_case_executions : "executed as"
    use_cases ||--o{ use_case_deployments : "deployed as"

    prompt_templates_v2 ||--o{ prompt_templates_v2 : "parent of"
    prompt_templates_v2 ||--o{ template_approvals : "requires approval"

    context_threads ||--o{ thread_messages : "contains messages"
    context_threads ||--o{ query_history : "groups queries"
    query_history ||--o{ query_history : "forked from"
```

### 3.2 Database Creation Script

```sql
-- Enhanced database schema for template-driven UI system

-- Users table (current implementation)
CREATE TABLE IF NOT EXISTS users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    username VARCHAR UNIQUE NOT NULL,
    full_name VARCHAR,
    email VARCHAR UNIQUE,
    hashed_password VARCHAR NOT NULL,
    role VARCHAR NOT NULL DEFAULT 'user',
    is_active BOOLEAN DEFAULT true,
    user_metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    last_login TIMESTAMPTZ
);

-- Use cases configuration table
CREATE TABLE use_cases (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    use_case_id VARCHAR(255) UNIQUE NOT NULL,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    category VARCHAR(100),
    intent_type VARCHAR(50) NOT NULL,
    version VARCHAR(20) NOT NULL,
    is_active BOOLEAN DEFAULT false,
    config_json JSON NOT NULL,
    created_by_user_id UUID REFERENCES users(id),
    approved_by_user_id UUID REFERENCES users(id),
    deployed_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Enhanced prompt templates with versioning
CREATE TABLE prompt_templates_v2 (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    template_id VARCHAR(255) NOT NULL,
    prompt_type VARCHAR(50) NOT NULL,
    version_number INTEGER NOT NULL,
    parent_template_id INTEGER REFERENCES prompt_templates_v2(id),
    template_content TEXT NOT NULL,
    variables JSON NOT NULL DEFAULT '[]',
    is_active_version BOOLEAN DEFAULT false,
    created_by_user_id UUID REFERENCES users(id),
    approved_by_user_id UUID REFERENCES users(id),
    deployment_status VARCHAR(20) DEFAULT 'draft',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(template_id, prompt_type, version_number)
);

-- UI components registry
CREATE TABLE ui_components (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    component_name VARCHAR(255) UNIQUE NOT NULL,
    component_type VARCHAR(50) NOT NULL,
    config_schema JSON NOT NULL,
    render_template TEXT NOT NULL,
    version VARCHAR(20) DEFAULT '1.0.0',
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Use case execution tracking
CREATE TABLE use_case_executions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    execution_id VARCHAR(255) UNIQUE NOT NULL,
    use_case_id INTEGER REFERENCES use_cases(id),
    user_id UUID REFERENCES users(id),
    input_data JSON NOT NULL,
    output_data JSON,
    status VARCHAR(20) DEFAULT 'running',
    execution_time_seconds FLOAT,
    error_message TEXT,
    started_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    completed_at TIMESTAMP WITH TIME ZONE
);

-- Template approval workflow
CREATE TABLE template_approvals (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    template_id INTEGER REFERENCES prompt_templates_v2(id),
    requested_by_user_id UUID REFERENCES users(id),
    approved_by_user_id UUID REFERENCES users(id),
    approval_status VARCHAR(20) DEFAULT 'pending',
    approval_notes TEXT,
    requested_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    approved_at TIMESTAMP WITH TIME ZONE
);

-- Use case deployment tracking
CREATE TABLE use_case_deployments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    use_case_id INTEGER REFERENCES use_cases(id),
    environment VARCHAR(50) DEFAULT 'production',
    deployment_status VARCHAR(20) DEFAULT 'active',
    deployed_by_user_id UUID REFERENCES users(id),
    deployment_config JSON,
    deployed_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    rolled_back_at TIMESTAMP WITH TIME ZONE
);

-- Query history table
CREATE TABLE query_history (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    query_id VARCHAR(255) UNIQUE NOT NULL,
    user_id UUID REFERENCES users(id),
    thread_id VARCHAR(255),
    parent_query_id VARCHAR(255) REFERENCES query_history(query_id),
    use_case_id VARCHAR(255) NOT NULL,
    use_case_name VARCHAR(255) NOT NULL,
    query_title VARCHAR(500) NOT NULL,
    input_data JSON NOT NULL,
    output_data JSON,
    execution_status VARCHAR(20) DEFAULT 'pending',
    execution_time_seconds FLOAT,
    error_message TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    is_favorite BOOLEAN DEFAULT false,
    tags JSON DEFAULT '[]',
    notes TEXT,
    fork_count INTEGER DEFAULT 0,
    is_forked BOOLEAN DEFAULT false,

    -- Security and encryption fields
    is_encrypted BOOLEAN DEFAULT false,
    encryption_key_id VARCHAR(255),
    encrypted_at TIMESTAMP WITH TIME ZONE,
    encryption_version VARCHAR(20) DEFAULT '1.0',
    data_classification VARCHAR(50) DEFAULT 'confidential'
);

-- Context threads table
CREATE TABLE context_threads (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    thread_id VARCHAR(255) UNIQUE NOT NULL,
    user_id UUID REFERENCES users(id),
    title VARCHAR(500) NOT NULL,
    description TEXT,
    context_size_tokens INTEGER DEFAULT 0,
    max_context_tokens INTEGER DEFAULT 8000,
    auto_compact BOOLEAN DEFAULT true,
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    last_activity_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    agent_config JSON DEFAULT '{}',
    multi_agent_workflow VARCHAR(255)
);

-- Thread messages table
CREATE TABLE thread_messages (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    message_id VARCHAR(255) UNIQUE NOT NULL,
    thread_id VARCHAR(255) REFERENCES context_threads(thread_id),
    message_type VARCHAR(50) NOT NULL,
    content TEXT NOT NULL,
    metadata JSON DEFAULT '{}',
    token_count INTEGER DEFAULT 0,
    query_id VARCHAR(255) REFERENCES query_history(query_id),
    use_case_id VARCHAR(255),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    agent_id VARCHAR(255),
    tool_calls JSON DEFAULT '[]',

    -- Security and encryption fields
    is_encrypted BOOLEAN DEFAULT false,
    encryption_key_id VARCHAR(255),
    encrypted_at TIMESTAMP WITH TIME ZONE,
    encryption_version VARCHAR(20) DEFAULT '1.0',
    data_classification VARCHAR(50) DEFAULT 'confidential'
);

-- Indexes for performance
CREATE INDEX idx_use_cases_active ON use_cases(is_active, category);
CREATE INDEX idx_prompt_templates_active ON prompt_templates_v2(template_id, is_active_version);
CREATE INDEX idx_executions_user_date ON use_case_executions(user_id, started_at);
CREATE INDEX idx_approvals_status ON template_approvals(approval_status, requested_at);
CREATE INDEX idx_query_history_user ON query_history(user_id, created_at);
CREATE INDEX idx_query_history_use_case ON query_history(use_case_id, created_at);
CREATE INDEX idx_context_threads_user ON context_threads(user_id, last_activity_at);
CREATE INDEX idx_thread_messages_thread ON thread_messages(thread_id, created_at);
CREATE INDEX idx_query_history_favorites ON query_history(user_id, is_favorite) WHERE is_favorite = true;
```

---

## UI Page Architecture

### 4.1 Main Application Structure

```mermaid
graph TB
    subgraph "Main App Layout"
        A[App Header] --> B[Navigation Sidebar]
        B --> C[Main Content Area]
        C --> D[Footer]
    end

    subgraph "Navigation Pages"
        E[Dashboard]
        F[Use Cases]
        G[Document Library]
        H[Analytics]
        I[Admin Panel]
        J[User Profile]
    end

    subgraph "Use Case Pages"
        K[Use Case Selector]
        L[Dynamic Form Generator]
        M[Results Display]
        N[Query History Sidebar]
        O[Context Thread Manager]
        P[Query Fork Interface]
    end

    subgraph "Admin Pages"
        Q[User Management]
        R[Template Editor]
        S[Use Case Builder]
        T[System Settings]
        U[Approval Workflow]
    end

    B --> E
    B --> F
    B --> G
    B --> H
    B --> I
    B --> J

    F --> K
    K --> L
    L --> M
    F --> N
    F --> O
    F --> P

    I --> Q
    I --> R
    I --> S
    I --> T
    I --> U

    classDef main fill:#e3f2fd
    classDef nav fill:#f3e5f5
    classDef usecase fill:#e8f5e8
    classDef admin fill:#fff3e0

    class A,B,C,D main
    class E,F,G,H,I,J nav
    class K,L,M,N,O,P usecase
    class Q,R,S,T,U admin
```

### 4.2 Use Case Interface Flow

```mermaid
sequenceDiagram
    participant U as User
    participant UI as Streamlit UI
    participant API as Orchestrator API
    participant DB as Database
    participant LLM as LLM Service

    U->>UI: Select Use Case
    UI->>API: GET /admin/use-cases/active
    API->>DB: Query active use cases
    DB-->>API: Return use cases list
    API-->>UI: Use cases data
    UI-->>U: Display use case selector

    U->>UI: Choose specific use case
    UI->>API: GET /admin/use-cases/{id}/config
    API->>DB: Get use case configuration
    DB-->>API: Return config JSON
    API-->>UI: Use case configuration
    UI-->>U: Generate dynamic form

    U->>UI: Fill form and submit
    UI->>UI: Validate inputs
    UI->>API: POST /api/v1/process
    API->>DB: Log execution
    API->>LLM: Process with prompts
    LLM-->>API: Return results
    API->>DB: Store results
    API-->>UI: Formatted response
    UI-->>U: Display results with visualizations
```

### 4.3 Admin Interface Pages

#### **4.3.1 Use Case Builder Interface**

```mermaid
graph LR
    subgraph "Use Case Builder Wizard"
        A[Step 1: Basic Info] --> B[Step 2: Prompts]
        B --> C[Step 3: RAG Config]
        C --> D[Step 4: UI Design]
        D --> E[Step 5: Output Format]
        E --> F[Step 6: Preview & Test]
        F --> G[Step 7: Deploy]
    end

    subgraph "Step 2: Prompts Detail"
        H[System Prompt Editor]
        I[User Prompt Editor]
        J[Tool Prompt Editor]
        K[Variable Manager]
        L[Template Inheritance]
    end

    subgraph "Step 4: UI Design Detail"
        M[Layout Selector]
        N[Input Field Designer]
        O[Validation Rules]
        P[Styling Options]
        Q[Help Content]
    end

    B --> H
    B --> I
    B --> J
    B --> K
    B --> L

    D --> M
    D --> N
    D --> O
    D --> P
    D --> Q
```

#### **4.3.2 Template Management Interface**

```mermaid
graph TB
    subgraph "Template Management Dashboard"
        A[Template Library] --> B[Template Editor]
        A --> C[Version History]
        A --> D[Approval Queue]

        B --> E[Syntax Highlighting]
        B --> F[Variable Management]
        B --> G[Preview Mode]
        B --> H[Save as Draft]

        C --> I[Version Comparison]
        C --> J[Rollback Options]

        D --> K[Pending Approvals]
        D --> L[Approval Actions]
        D --> M[Deployment Pipeline]
    end

    subgraph "Template Editor Features"
        N[Code Editor with Jinja2 Syntax]
        O[Variable Autocomplete]
        P[Template Validation]
        Q[Live Preview]
        R[Version Control]
    end

    E --> N
    F --> O
    G --> P
    G --> Q
    H --> R
```

---

## Streamlit Best Practices Implementation

### 5.1 State Management

```python
class SessionStateManager:
    """Centralized session state management"""

    @staticmethod
    def init_session_state():
        """Initialize session state with default values"""
        defaults = {
            'current_user': None,
            'selected_use_case': None,
            'form_data': {},
            'execution_history': [],
            'theme': 'default'
        }

        for key, value in defaults.items():
            if key not in st.session_state:
                st.session_state[key] = value

    @staticmethod
    def get_user_inputs(use_case_id: str) -> Dict:
        """Get user inputs for specific use case"""
        key = f"inputs_{use_case_id}"
        return st.session_state.get(key, {})

    @staticmethod
    def save_user_inputs(use_case_id: str, inputs: Dict):
        """Save user inputs for specific use case"""
        key = f"inputs_{use_case_id}"
        st.session_state[key] = inputs
```

### 5.2 Caching Strategy

```python
@st.cache_data(ttl=300)  # 5-minute cache
def load_use_cases() -> List[Dict]:
    """Cached loading of active use cases"""
    return api_client.get_active_use_cases()

@st.cache_data(ttl=600)  # 10-minute cache
def load_use_case_config(use_case_id: str) -> UseCaseConfig:
    """Cached loading of use case configuration"""
    return api_client.get_use_case_config(use_case_id)

@st.cache_resource
def get_api_client() -> APIClient:
    """Singleton API client"""
    return APIClient(base_url=st.secrets["api_base_url"])
```

### 5.3 Error Handling and User Feedback

```python
class UIErrorHandler:
    """Centralized error handling with user-friendly messages"""

    @staticmethod
    def handle_api_error(error: Exception, context: str = ""):
        """Handle API errors with appropriate user messages"""
        if isinstance(error, httpx.HTTPStatusError):
            if error.response.status_code == 401:
                st.error("🔒 Authentication required. Please log in.")
                st.stop()
            elif error.response.status_code == 403:
                st.error("🚫 You don't have permission for this action.")
            elif error.response.status_code == 404:
                st.error(f"📭 {context} not found.")
            elif error.response.status_code >= 500:
                st.error("🔧 Server error. Please try again later.")
            else:
                st.error(f"❌ Request failed: {error.response.status_code}")
        else:
            st.error(f"💥 Unexpected error: {str(error)}")

    @staticmethod
    def show_success(message: str):
        """Show success message with icon"""
        st.success(f"✅ {message}")

    @staticmethod
    def show_warning(message: str):
        """Show warning message with icon"""
        st.warning(f"⚠️ {message}")
```

### 5.4 Responsive Design

```python
class ResponsiveLayout:
    """Responsive layout utilities for different screen sizes"""

    @staticmethod
    def get_columns_config() -> List[int]:
        """Get column configuration based on screen size"""
        # This would be enhanced with actual screen size detection
        return [1, 2, 1]  # sidebar, main, info

    @staticmethod
    def create_card(title: str, content: str, color: str = "white"):
        """Create styled card component"""
        st.markdown(f"""
        <div style="
            background-color: {color};
            padding: 1rem;
            border-radius: 0.5rem;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            margin: 0.5rem 0;
        ">
            <h3 style="margin-top: 0;">{title}</h3>
            <p>{content}</p>
        </div>
        """, unsafe_allow_html=True)
```

### 5.5 Performance Optimization

```python
class PerformanceOptimizer:
    """Performance optimization utilities"""

    @staticmethod
    def paginate_results(data: List, page_size: int = 10):
        """Implement pagination for large datasets"""
        if not data:
            return data, 0, 0

        total_pages = (len(data) - 1) // page_size + 1

        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            page = st.selectbox(
                "Page",
                options=range(1, total_pages + 1),
                key="pagination"
            )

        start_idx = (page - 1) * page_size
        end_idx = start_idx + page_size

        return data[start_idx:end_idx], page, total_pages

    @staticmethod
    def lazy_load_component(load_func, placeholder_text="Loading..."):
        """Lazy load expensive components"""
        placeholder = st.empty()
        placeholder.info(placeholder_text)

        try:
            result = load_func()
            placeholder.empty()
            return result
        except Exception as e:
            placeholder.error(f"Failed to load: {str(e)}")
            return None
```

---

## Development Workflow

### 6.1 Use Case Development Process

```mermaid
graph TD
    A[Developer Creates Use Case] --> B[Define Prompts]
    B --> C[Configure RAG Parameters]
    C --> D[Design UI Layout]
    D --> E[Set Output Format]
    E --> F[Test in Development]
    F --> G{Tests Pass?}
    G -->|No| B
    G -->|Yes| H[Submit for Approval]
    H --> I[Admin Reviews]
    I --> J{Approved?}
    J -->|No| K[Request Changes]
    K --> B
    J -->|Yes| L[Deploy to Production]
    L --> M[Monitor Usage]
    M --> N[Collect Feedback]
    N --> O[Iterate]
    O --> B
```

### 6.2 Template Development Guidelines

1. **Prompt Template Structure**:
   - Use clear variable naming: `{user_query}`, `{context}`, `{timeframe}`
   - Include validation rules for required variables
   - Provide examples in template comments

2. **UI Configuration Best Practices**:
   - Group related fields in sections
   - Use appropriate field types for data validation
   - Provide helpful placeholder text and tooltips
   - Include conditional field display logic

3. **Output Configuration Guidelines**:
   - Define primary display for main results
   - Use secondary displays for additional details
   - Configure appropriate download formats
   - Include visualization for data-heavy results

### 6.3 Testing Framework

```python
class UseCaseTestFramework:
    """Testing framework for use cases"""

    def __init__(self, use_case_config: UseCaseConfig):
        self.config = use_case_config

    def test_ui_generation(self) -> List[str]:
        """Test UI generation from configuration"""
        errors = []

        # Test required fields
        for section in self.config.ui_config.input_sections:
            for field in section.fields:
                if field.required and not field.default_value:
                    # Test that validation catches missing required fields
                    pass

        return errors

    def test_prompt_variables(self) -> List[str]:
        """Test that all prompt variables are covered by UI fields"""
        errors = []

        # Get all variables from prompts
        all_variables = set()
        for prompt in self.config.prompts.values():
            all_variables.update(prompt.variables)

        # Get all field names from UI
        ui_fields = set()
        for section in self.config.ui_config.input_sections:
            for field in section.fields:
                ui_fields.add(field.field_name)

        # Check for missing variables
        missing = all_variables - ui_fields
        if missing:
            errors.append(f"Missing UI fields for variables: {missing}")

        return errors

    def test_execution(self, sample_inputs: Dict) -> bool:
        """Test use case execution with sample inputs"""
        try:
            # This would call the actual API with test inputs
            result = self._execute_use_case(sample_inputs)
            return result is not None
        except Exception:
            return False
```

---

## Enterprise Air-Gapped Deployment Considerations

### **Key Management for Air-Gapped Environments**

Since the application will run in enterprise environments without cloud provider access, the security architecture must be adapted for on-premises deployment:

#### **Enterprise Key Management Options**

```python
class EnterpriseKeyManager:
    """Key management for air-gapped enterprise environments"""

    def __init__(self, deployment_type: str = "hsm"):
        self.deployment_type = deployment_type
        self.configure_key_management()

    def configure_key_management(self):
        """Configure key management based on enterprise infrastructure"""

        if self.deployment_type == "hsm":
            # Hardware Security Module integration
            self.key_provider = HSMKeyProvider()
        elif self.deployment_type == "vault":
            # HashiCorp Vault integration
            self.key_provider = VaultKeyProvider()
        elif self.deployment_type == "file_based":
            # Secure file-based key storage (fallback option)
            self.key_provider = FileBasedKeyProvider()
        else:
            raise ValueError(f"Unsupported deployment type: {self.deployment_type}")

class HSMKeyProvider:
    """Hardware Security Module integration via PKCS#11"""

    def __init__(self):
        # Configuration for enterprise HSM
        self.pkcs11_library = "/usr/lib/pkcs11/libpkcs11.so"  # Enterprise HSM library
        self.slot_id = 0
        self.pin = None  # Retrieved from secure configuration

    def get_encryption_key(self, user_id: str) -> bytes:
        """Retrieve encryption key from HSM"""
        # Implementation would use PyKCS11 or similar library
        # to interact with enterprise HSM
        pass

    def create_user_key(self, user_id: str) -> str:
        """Create new encryption key in HSM"""
        # Generate key in HSM and return key handle/reference
        pass

    def rotate_key(self, key_reference: str) -> str:
        """Rotate existing key in HSM"""
        pass

class VaultKeyProvider:
    """HashiCorp Vault integration for key management"""

    def __init__(self):
        # Vault configuration for enterprise deployment
        self.vault_url = "https://vault.internal.company.com:8200"
        self.vault_token = None  # Retrieved from secure configuration
        self.key_mount = "kv-v2"
        self.key_path_prefix = "aio/encryption-keys"

    def get_encryption_key(self, user_id: str) -> bytes:
        """Retrieve encryption key from Vault"""
        import hvac  # HashiCorp Vault client

        client = hvac.Client(url=self.vault_url, token=self.vault_token)

        try:
            response = client.secrets.kv.v2.read_secret_version(
                path=f"{self.key_path_prefix}/{user_id}",
                mount_point=self.key_mount
            )
            return response['data']['data']['encryption_key'].encode()
        except Exception as e:
            # Handle key retrieval errors
            raise KeyManagementError(f"Failed to retrieve key for user {user_id}: {e}")

    def create_user_key(self, user_id: str) -> str:
        """Create new encryption key in Vault"""
        import secrets

        # Generate cryptographically secure key
        encryption_key = secrets.token_bytes(32)  # 256-bit key
        key_id = f"user_{user_id}_{int(time.time())}"

        client = hvac.Client(url=self.vault_url, token=self.vault_token)

        # Store key in Vault
        client.secrets.kv.v2.create_or_update_secret(
            path=f"{self.key_path_prefix}/{user_id}",
            secret={
                'encryption_key': encryption_key.hex(),
                'created_at': datetime.now().isoformat(),
                'algorithm': 'AES-256-GCM',
                'key_id': key_id
            },
            mount_point=self.key_mount
        )

        return key_id

class FileBasedKeyProvider:
    """Secure file-based key storage (fallback for basic deployments)"""

    def __init__(self):
        # Secure directory for key storage
        self.key_directory = "/opt/aio/secure/keys"
        self.master_key_file = "/opt/aio/secure/master.key"

        # Ensure secure permissions (600 - owner read/write only)
        os.chmod(self.key_directory, 0o700)
        os.chmod(self.master_key_file, 0o600)

    def get_encryption_key(self, user_id: str) -> bytes:
        """Retrieve user key from secure file storage"""
        from cryptography.fernet import Fernet
        from cryptography.hazmat.primitives import hashes
        from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

        # Load master key
        with open(self.master_key_file, 'rb') as f:
            master_key = f.read()

        # Derive user-specific key
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=user_id.encode(),
            iterations=100000,
        )
        user_key = kdf.derive(master_key)

        return user_key
```

#### **Certificate Management for Air-Gapped TLS**

```python
class EnterpriseCertificateManager:
    """Certificate management for air-gapped enterprise deployment"""

    def __init__(self):
        self.ca_cert_path = "/opt/aio/certs/ca.crt"
        self.server_cert_path = "/opt/aio/certs/server.crt"
        self.server_key_path = "/opt/aio/certs/server.key"
        self.client_ca_path = "/opt/aio/certs/client-ca.crt"

    def configure_tls_context(self):
        """Configure TLS context for enterprise environment"""
        import ssl

        context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)

        # Load enterprise CA certificate
        context.load_verify_locations(self.ca_cert_path)

        # Load server certificate and key
        context.load_cert_chain(self.server_cert_path, self.server_key_path)

        # Configure for enterprise security
        context.minimum_version = ssl.TLSVersion.TLSv1_3
        context.maximum_version = ssl.TLSVersion.TLSv1_3

        # Require client certificates for mutual TLS (optional)
        context.verify_mode = ssl.CERT_REQUIRED
        context.load_verify_locations(self.client_ca_path)

        return context
```

#### **Enterprise Deployment Configuration**

```yaml
# docker-compose.enterprise.yml
version: '3.8'

services:
  orchestrator-api:
    image: aio/orchestrator:latest
    environment:
      # Enterprise security configuration
      - ENCRYPTION_PROVIDER=hsm  # or 'vault' or 'file_based'
      - HSM_PKCS11_LIBRARY=/usr/lib/pkcs11/libpkcs11.so
      - VAULT_URL=https://vault.internal.company.com:8200
      - VAULT_TOKEN_FILE=/run/secrets/vault_token

      # Certificate paths
      - TLS_CERT_PATH=/opt/certs/server.crt
      - TLS_KEY_PATH=/opt/certs/server.key
      - TLS_CA_PATH=/opt/certs/ca.crt

      # Enterprise database
      - DATABASE_URL=postgresql://user:pass@postgres.internal:5432/aio

      # No cloud dependencies
      - DISABLE_CLOUD_FEATURES=true
      - OFFLINE_MODE=true

    volumes:
      # Mount enterprise certificates
      - /enterprise/certs:/opt/certs:ro

      # Mount HSM library (if using HSM)
      - /usr/lib/pkcs11:/usr/lib/pkcs11:ro

      # Mount secure key storage
      - /enterprise/secure:/opt/aio/secure:ro

    secrets:
      - vault_token
      - hsm_pin

    networks:
      - enterprise_network

  postgres:
    image: postgres:17
    environment:
      - POSTGRES_DB=aio
      - POSTGRES_USER=aio_user
      - POSTGRES_PASSWORD_FILE=/run/secrets/db_password

    volumes:
      # Enterprise-managed persistent storage
      - /enterprise/data/postgres:/var/lib/postgresql/data

      # Custom PostgreSQL configuration for enterprise
      - /enterprise/config/postgresql.conf:/etc/postgresql/postgresql.conf

    secrets:
      - db_password

secrets:
  vault_token:
    file: /enterprise/secrets/vault_token
  hsm_pin:
    file: /enterprise/secrets/hsm_pin
  db_password:
    file: /enterprise/secrets/db_password

networks:
  enterprise_network:
    driver: bridge
    ipam:
      config:
        - subnet: 172.20.0.0/16
```

#### **Enterprise Security Hardening**

```bash
#!/bin/bash
# enterprise_security_setup.sh

# Set secure file permissions
chmod 600 /enterprise/secrets/*
chmod 700 /enterprise/secure/keys
chown -R aio:aio /enterprise/secure

# Configure firewall rules (example for iptables)
iptables -A INPUT -p tcp --dport 8000 -s 192.0.2.0/24 -j ACCEPT  # Example: internal/admin network
iptables -A INPUT -p tcp --dport 8000 -j DROP  # Block external access

# Set up log monitoring
rsyslog_config="
# AI Operations Platform (AIOP) security logging
local0.*    /var/log/aio/security.log
& stop
"
echo "$rsyslog_config" >> /etc/rsyslog.conf

# Configure log rotation
logrotate_config="
/var/log/aio/*.log {
    daily
    rotate 90
    compress
    delaycompress
    missingok
    create 640 aio aio
    postrotate
        systemctl reload rsyslog
    endscript
}
"
echo "$logrotate_config" > /etc/logrotate.d/aio

# Set up intrusion detection
fail2ban_config="
[aio]
enabled = true
port = 8000
filter = aio
logpath = /var/log/aio/security.log
maxretry = 3
bantime = 3600
"
echo "$fail2ban_config" > /etc/fail2ban/jail.d/aio.conf
```

---

## Security Implementation Checklist

### **Encryption Requirements (Enterprise Air-Gapped Environment)**

- [ ] **Data at Rest**: All conversation history encrypted using AES-256-GCM
- [ ] **Data in Transit**: TLS 1.3 for all API communications
- [ ] **Field-Level Encryption**: Sensitive fields encrypted individually
- [ ] **Key Management**: Enterprise HSM or HashiCorp Vault integration
- [ ] **Key Rotation**: Automated 90-day key rotation cycle
- [ ] **User Isolation**: Row-level security policies enforced
- [ ] **Air-Gap Compliance**: No external cloud dependencies for encryption

### **Access Control**

- [ ] **Authentication**: JWT-based authentication with refresh tokens
- [ ] **Authorization**: Role-based access control (Admin/Analyst/User)
- [ ] **Data Isolation**: Users can only access their own conversation history
- [ ] **Audit Logging**: All data access logged with IP, user agent, timestamps
- [ ] **Session Management**: Secure session handling with timeout

### **Transport Security**

- [ ] **HTTPS Only**: All endpoints require HTTPS
- [ ] **Security Headers**: HSTS, CSP, X-Frame-Options configured
- [ ] **Certificate Validation**: Strict certificate validation
- [ ] **API Security**: Rate limiting and input validation

### **Compliance Features**

- [ ] **Data Classification**: Conversation data marked as confidential
- [ ] **Retention Policies**: Configurable data retention periods
- [ ] **Right to Deletion**: User data deletion capabilities
- [ ] **Export Controls**: Encrypted data export for compliance
- [ ] **Audit Trail**: Complete audit trail for security reviews

### **Enterprise Air-Gap Requirements**

- [ ] **No Cloud Dependencies**: All encryption/key management on-premises
- [ ] **HSM Integration**: Hardware Security Module support via PKCS#11
- [ ] **Vault Integration**: HashiCorp Vault for key management
- [ ] **File-Based Fallback**: Secure file-based key storage option
- [ ] **Enterprise Certificates**: Support for internal CA certificates
- [ ] **Network Isolation**: Configurable for internal networks only
- [ ] **Offline Operation**: Full functionality without internet access

---

## Conclusion

This comprehensive reference document provides the foundation for developing a sophisticated, template-driven UI system for AI Operations Platform. The system enables:

1. **Zero-code use case development** through configuration
2. **Flexible UI generation** from JSON templates
3. **Comprehensive admin interfaces** for template and user management
4. **Robust approval workflows** for enterprise deployment
5. **Performance-optimized Streamlit implementation** following best practices
6. **Enterprise-grade security** with encryption at rest and in transit
7. **Future-ready architecture** for multi-agent AI systems

The modular architecture ensures that new use cases can be rapidly developed and deployed without requiring changes to the core Streamlit application, while maintaining the highest security standards for sensitive conversation data.

**Enterprise Air-Gapped Deployment**: The system is specifically designed for enterprise environments without cloud provider access, featuring:

- Multiple key management options (HSM, Vault, file-based)
- On-premises certificate management
- Network isolation capabilities
- Complete offline operation support

The system achieves the goal of maximum flexibility and code reusability while ensuring enterprise-grade security and compliance in air-gapped environments.
