# Modelos SQLAlchemy do TradeAI
# Importar aqui para garantir registro no metadata do Base
from app.models import system      # noqa: F401
from app.models import market      # noqa: F401
from app.models import indicators  # noqa: F401
from app.models import paper_trading  # noqa: F401
from app.models import market_context  # noqa: F401
from app.models import analytics       # noqa: F401
from app.models import market_structure  # noqa: F401
from app.models import smart_money       # noqa: F401
from app.models import optimizer         # noqa: F401
from app.models import alpha             # noqa: F401
from app.models import robustness        # noqa: F401
from app.models import strategies        # noqa: F401
from app.models import trade_management  # noqa: F401

from app.models.scalper import ScalperAccount, ScalperTrade, ScalperRiskDaily, ScalperSignal
from app.models import biel  # noqa: F401
