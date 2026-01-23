# OHM Demo Interface

Streamlit-based demonstration interface for Open Hardware Manager (OHM) multi-facility matching capabilities.

## Setup

### Install Dependencies

```bash
conda activate supply-graph-ai
pip install -r requirements.txt
```

This will install Streamlit and other required dependencies.

### Run the Demo

```bash
streamlit run demo/app.py
```

The app will open in your browser at `http://localhost:8501`.

## Configuration

### API URL

The demo connects to the OHM API. By default, it uses:
- **Cloud Run**: `https://supply-graph-ai-1085931013579.us-west1.run.app`

You can override this with an environment variable:

```bash
export CLOUD_RUN_URL="https://your-api-url.com"
streamlit run demo/app.py
```

Or use a local deployment:

```bash
export CLOUD_RUN_URL="http://localhost:8001"
streamlit run demo/app.py
```

## Structure

- `app.py` - Main Streamlit application
- `api_client.py` - API client for interacting with OHM API
- `infrastructure/` - Infrastructure verification tools

## Development Status

**Current**: Basic structure created (Task 3.1.1)

**Next Steps**:
- Task 3.1.2: Configure Streamlit for presentation
- Task 3.2: Map visualization
- Task 3.3: OKH design selection
- Task 3.4: Matching execution
- Task 3.5: Results display
- Task 3.6: RFQ display

See `notes/item3-implementation-plan.md` for full implementation plan.
