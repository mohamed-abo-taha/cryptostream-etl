"""Start the REST API that serves the warehoused data.

    python run_api.py        # then open http://127.0.0.1:5000/coins
"""

import config
from src.api import create_app

app = create_app(config.DB_PATH)

if __name__ == "__main__":
    app.run(host=config.API_HOST, port=config.API_PORT, debug=False)
