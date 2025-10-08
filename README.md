# Supervised Multi-Agent Onboarding System

A production-ready supervised multi-agent system for user onboarding, built with LangGraph and Python.

## 🚀 Features

- **Supervised Workflow**: Centralized orchestration of multiple agents
- **Sequential Processing**: Ensures data consistency and predictable flow
- **State-Based Routing**: Automatic progression through onboarding steps
- **Progress Tracking**: Real-time visibility into completion status
- **Subgraph Integration**: Validation and API call handling
- **RESTful API**: Flask-based endpoints for easy integration

## 📋 Architecture

```
┌─────────────────────┐
│    SUPERVISOR       │ (Decision Maker)
│  (State-Based)      │
└──────────┬──────────┘
           │
     ┌─────┴──────┬──────────┬──────────┐
     │            │          │          │
┌────▼───┐  ┌────▼───┐ ┌───▼────┐ ┌───▼────┐
│ Signup │→ │Company │→│  KYC   │→│  Bank  │→ Complete
└────────┘  └────────┘ └────────┘ └────────┘
```

### Sequential Workflow

1. **Signup Agent** - User registration (name, email, phone)
2. **Company Agent** - Business details (company name, GST)
3. **KYC Agent** - Verification (PAN, Aadhar, GST documents)
4. **Bank Agent** - Banking info (account, IFSC)
5. **Complete** - Onboarding finalization

## 🛠️ Installation

### 1. Clone Repository
```bash
cd "c:\Users\ambbu\OneDrive\Desktop\AI&ML\AI Projects\multi model"
```

### 2. Create Virtual Environment
```bash
python -m venv venv
venv\Scripts\activate
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

## 🎯 Quick Start

### Start the API Server

```bash
python app.py
```

Server runs on: `http://localhost:5000`

### Test with cURL

**Health Check:**
```bash
curl http://localhost:5000/health
```

**Complete Onboarding:**
```bash
curl -X POST http://localhost:5000/chat \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Name: John Doe, Email: john@example.com, Phone: 555-1234. Company: Tech Corp, GST: 29ABCDE1234F1Z5. PAN: ABCDE1234F, Aadhar: 123456789012. Bank: HDFC, Account: 12345678901234, IFSC: HDFC0001234",
    "session_id": "test123"
  }'
```

### Test with Python

```bash
python test_supervised_api.py
```

### Run Examples

```bash
python example_supervised_onboarding.py
python example_llm_usage.py
```

## 📡 API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/health` | Health check |
| `POST` | `/chat` | Main supervised onboarding |
| `POST` | `/chat/legacy` | Legacy graph supervisor |
| `GET` | `/graph/visualize` | Workflow visualization |
| `GET` | `/graph/legacy/visualize` | Legacy visualization |

### Example Request

```json
{
    "message": "I want to sign up. Name: Alice Smith, Email: alice@example.com",
    "session_id": "session_123"
}
```

### Example Response

```json
{
    "response": "📋 Supervisor: Starting with signup process...",
    "session_id": "session_123",
    "status": "in_progress",
    "onboarding_id": null,
    "progress": {
        "signup": true,
        "company": false,
        "kyc": false,
        "bank": false
    },
    "metadata": {
        "supervised": true,
        "sequential_workflow": true
    }
}
```

## 📂 Project Structure

```
multi model/
├── agents/
│   ├── supervised_onboarding.py    # Main supervised system ⭐
│   ├── signup_agent.py             # Signup handling
│   ├── company_details_agent.py    # Company info
│   ├── kyc_agent.py                # KYC verification
│   ├── bank_details_agent.py       # Bank details
│   ├── supervisor/
│   │   └── graph_supervisor.py     # Legacy system
│   ├── subgraphs/
│   │   ├── validation_subgraph.py  # Data validation
│   │   └── api_subgraph.py         # API calls
│   └── state/
│       └── graph_state.py          # State management
├── database/
│   ├── models.py                   # Database models
│   └── state_manager.py            # State persistence
├── config/
│   └── llm_config.py               # LLM configuration
├── app.py                          # Flask application ⭐
├── test_supervised_api.py          # API tests ⭐
├── example_supervised_onboarding.py # Usage examples ⭐
├── example_llm_usage.py            # LLM examples
├── SUPERVISED_ONBOARDING_GUIDE.md  # Full documentation ⭐
├── API_ENDPOINTS.md                # API reference ⭐
├── LLM_INTEGRATION_GUIDE.md        # LLM guide
└── requirements.txt                # Dependencies
```

## 🔑 Key Components

### Supervised System (`agents/supervised_onboarding.py`)

```python
from agents.supervised_onboarding import SupervisedOnboardingSystem

system = SupervisedOnboardingSystem()
result = system.process_onboarding("I want to sign up", "session_001")

print(result['status'])      # 'in_progress' or 'completed'
print(result['progress'])    # Progress tracking
```

### Individual Agents

Each agent handles a specific domain:
- **SignupAgent**: User information
- **CompanyDetailsAgent**: Business data
- **KYCAgent**: Document verification (with sub-agents for PAN/Aadhar/GST)
- **BankDetailsAgent**: Banking information

### Subgraphs

Shared functionality:
- **Validation Subgraph**: Data validation logic
- **API Subgraph**: External API integration

## 📖 Documentation

- **[SUPERVISED_ONBOARDING_GUIDE.md](SUPERVISED_ONBOARDING_GUIDE.md)** - Complete architecture guide
- **[API_ENDPOINTS.md](API_ENDPOINTS.md)** - API reference and examples
- **[LLM_INTEGRATION_GUIDE.md](LLM_INTEGRATION_GUIDE.md)** - LLM integration details

## 🧪 Testing

### Automated Test Suite

```bash
python test_supervised_api.py
```

Tests include:
- Health check
- Complete onboarding (single message)
- Step-by-step onboarding
- Legacy endpoint comparison
- Graph visualization

### Manual Testing

```bash
# Start server
python app.py

# In another terminal
curl http://localhost:5000/health

# Get visualization
curl http://localhost:5000/graph/visualize -o workflow.png
```

## 🔄 Workflow Example

**Step 1: Signup**
```json
POST /chat
{
    "message": "Name: John Doe, Email: john@example.com",
    "session_id": "s1"
}
→ Progress: signup=true, company=false, kyc=false, bank=false
```

**Step 2: Company**
```json
POST /chat
{
    "message": "Company: Tech Corp, GST: 29ABCDE1234F1Z5",
    "session_id": "s1"
}
→ Progress: signup=true, company=true, kyc=false, bank=false
```

**Step 3: KYC**
```json
POST /chat
{
    "message": "PAN: ABCDE1234F, Aadhar: 123456789012",
    "session_id": "s1"
}
→ Progress: signup=true, company=true, kyc=true, bank=false
```

**Step 4: Bank**
```json
POST /chat
{
    "message": "Bank: HDFC, Account: 12345678901234, IFSC: HDFC0001234",
    "session_id": "s1"
}
→ Progress: signup=true, company=true, kyc=true, bank=true
→ Status: completed, Onboarding ID: ONB_XXXXXXXX
```

## 🛡️ Features

- ✅ **Supervised Workflow** - Centralized orchestration
- ✅ **Sequential Processing** - Predictable execution order
- ✅ **State Management** - Automatic progress tracking
- ✅ **Subgraph Integration** - Reusable validation/API logic
- ✅ **LangGraph** - Production-ready agent framework
- ✅ **RESTful API** - Easy integration
- ✅ **Backward Compatible** - Legacy endpoints available
- ✅ **Comprehensive Docs** - Full guides and examples

## 🔧 Configuration

Environment variables (optional):
```bash
LOG_LEVEL=INFO
CHECKPOINT_DB=checkpoints.db
FLASK_DEBUG=False
SECRET_KEY=your-secret-key
```

## 📊 Monitoring

Check system status:
```bash
curl http://localhost:5000/health
```

Response:
```json
{
    "status": "healthy",
    "version": "3.0.0",
    "features": {
        "supervised_workflow": true,
        "sequential_processing": true,
        "state_based_routing": true
    }
}
```

## 🤝 Contributing

This is a learning project based on the supervised pattern from `multiaiagent.ipynb` in the Agentic-LanggraphCrash-course.

## 📝 License

MIT License - See course materials for details

## 🙏 Acknowledgments

- Built with [LangGraph](https://github.com/langchain-ai/langgraph)
- Based on supervised pattern from Agentic LangGraph crash course
- Inspired by multi-agent orchestration patterns

## 📞 Support

For questions or issues:
1. Check the documentation in `SUPERVISED_ONBOARDING_GUIDE.md`
2. Review API examples in `API_ENDPOINTS.md`
3. Run test suite: `python test_supervised_api.py`

---

**🚀 Ready to start?**

```bash
python app.py
```

Then open: http://localhost:5000/health

**Happy coding! 🎉**
