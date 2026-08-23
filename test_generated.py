import sys
import os

sys.path.append(os.path.abspath('modern-invoices/atm-login'))
from actionPerformed_function import calculate_actionPerformed

req = {
    "action": "login",
    "cardno": "' OR '1'='1",
    "pin": "' OR '1'='1"
}
res = calculate_actionPerformed(req)
print("Result:", res)
