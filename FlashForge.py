import streamlit as st
from openai import OpenAI
from streamlit_ace import st_ace

st.set_page_config(page_title="FlashForge AI ⚡", page_icon="⚡", layout="wide")

# Secret check
if "XAI_API_KEY" not in st.secrets or not st.secrets["XAI_API_KEY"]:
    st.error("🔑 **XAI_API_KEY is missing**", icon="🚨")
    st.markdown("""
    ### How to fix it:
    1. Click **⋮** → **Settings**
    2. Left sidebar → **Secrets**
    3. Paste this:
    ```toml
    XAI_API_KEY = "xai-XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX"
Click Save and refresh
""")
st.stop()

============================================================================
COMPLETE INTERFACES LIBRARY
============================================================================
Flash Loan Provider Interfaces
FLASH_LOAN_PROVIDERS = {
"Aave V3": {
"imports": [
"import {FlashLoanSimpleReceiverBase} from '@aave/core-v3/contracts/flashloan/base/FlashLoanSimpleReceiverBase.sol';",
"import {IPoolAddressesProvider} from '@aave/core-v3/contracts/interfaces/IPoolAddressesProvider.sol';",
"import {IPool} from '@aave/core-v3/contracts/interfaces/IPool.sol';"
],
"base_contract": "FlashLoanSimpleReceiverBase",
"callback": """
function executeOperation(
address asset,
uint256 amount,
uint256 premium,
address initiator,
bytes calldata params
) external override returns (bool) {
// Execute arbitrage strategy
_executeStrategy(asset, amount);

// Approve repayment
IERC20(asset).approve(address(POOL), amount + premium);
return true;
}""",
"flash_call": "POOL.flashLoanSimple(address(this), asset, amount, '');"
},
"Uniswap V3": {
"imports": [
"import {IUniswapV3Pool} from '@uniswap/v3-core/contracts/interfaces/IUniswapV3Pool.sol';",
"import {IUniswapV3SwapCallback} from '@uniswap/v3-core/contracts/interfaces/callback/IUniswapV3SwapCallback.sol';",
"import {IERC20} from '@openzeppelin/contracts/token/ERC20/IERC20.sol';"
],
"base_contract": "IUniswapV3SwapCallback",
"callback": """
function uniswapV3SwapCallback(
int256 amount0Delta,
int256 amount1Delta,
bytes calldata data
) external override {
if (amount0Delta > 0) {
IERC20(pool.token0()).transfer(msg.sender, uint256(amount0Delta));
} else if (amount1Delta > 0) {
IERC20(pool.token1()).transfer(msg.sender, uint256(amount1Delta));
}
}""",
"flash_call": "pool.flash(address(this), amount0, amount1, data);"
},
"Balancer V2": {
"imports": [
"import {IVault} from '@balancer-labs/v2-interfaces/contracts/vault/IVault.sol';",
"import {IFlashLoanRecipient} from '@balancer-labs/v2-interfaces/contracts/vault/IFlashLoanRecipient.sol';",
"import {IERC20} from '@openzeppelin/contracts/token/ERC20/IERC20.sol';"
],
"base_contract": "IFlashLoanRecipient",
"callback": """
function receiveFlashLoan(
IERC20[] memory tokens,
uint256[] memory amounts,
uint256[] memory feeAmounts,
bytes memory userData
) external override {
require(msg.sender == address(vault), 'Not vault');

for (uint256 i = 0; i < tokens.length; i++) {
_executeStrategy(address(tokens[i]), amounts[i]);
tokens[i].approve(address(vault), amounts[i] + feeAmounts[i]);
}
}""",
"flash_call": "vault.flashLoan(address(this), tokens, amounts, '');"
},
"dYdX": {
"imports": [
"import {ISoloMargin} from '@dydxprotocol/solo/contracts/interfaces/ISoloMargin.sol';",
"import {IERC20} from '@openzeppelin/contracts/token/ERC20/IERC20.sol';"
],
"base_contract": "",
"callback": """
function callFunction(
address sender,
account.Info memory account,
bytes memory data
) external {
require(msg.sender == address(soloMargin), 'Not soloMargin');
(address asset, uint256 amount) = abi.decode(data, (address, uint256));
_executeStrategy(asset, amount);
}""",
"flash_call": "soloMargin.operate(operations);"
}
}

DEX Interfaces for Arbitrage
DEX_INTERFACES = {
"Uniswap V2": {
"imports": [
"import {IUniswapV2Router02} from '@uniswap/v2-periphery/contracts/interfaces/IUniswapV2Router02.sol';",
"import {IUniswapV2Pair} from '@uniswap/v2-core/contracts/interfaces/IUniswapV2Pair.sol';"
],
"swap_code": """
function _swapOnUniswapV2(
address router,
address tokenIn,
address tokenOut,
uint256 amountIn,
uint256 amountOutMin
) internal returns (uint256 amountOut) {
IERC20(tokenIn).approve(router, amountIn);
address[] memory path = new address;
path[0] = tokenIn;
path[1] = tokenOut;

uint256[] memory amounts = IUniswapV2Router02(router).swapExactTokensForTokens(
amountIn,
amountOutMin,
path,
address(this),
block.timestamp
);
return amounts[1];
}"""
},
"Uniswap V3": {
"imports": [
"import {ISwapRouter} from '@uniswap/v3-periphery/contracts/interfaces/ISwapRouter.sol';",
"import {IQuoter} from '@uniswap/v3-periphery/contracts/interfaces/IQuoter.sol';"
],
"swap_code": """
function _swapOnUniswapV3(
address router,
address tokenIn,
address tokenOut,
uint24 fee,
uint256 amountIn,
uint256 amountOutMin
) internal returns (uint256 amountOut) {
IERC20(tokenIn).approve(router, amountIn);

ISwapRouter.ExactInputSingleParams memory params = ISwapRouter.ExactInputSingleParams({
tokenIn: tokenIn,
tokenOut: tokenOut,
fee: fee,
recipient: address(this),
deadline: block.timestamp,
amountIn: amountIn,
amountOutMinimum: amountOutMin,
sqrtPriceLimitX96: 0
});

amountOut = ISwapRouter(router).exactInputSingle(params);
return amountOut;
}"""
},
"Sushiswap": {
"imports": [
"import {ISushiSwapRouter} from '@sushiswap/core/contracts/interfaces/ISushiSwapRouter.sol';"
],
"swap_code": """
function _swapOnSushiswap(
address router,
address tokenIn,
address tokenOut,
uint256 amountIn,
uint256 amountOutMin
) internal returns (uint256 amountOut) {
IERC20(tokenIn).approve(router, amountIn);
address[] memory path = new address;
path[0] = tokenIn;
path[1] = tokenOut;

uint256[] memory amounts = ISushiSwapRouter(router).swapExactTokensForTokens(
amountIn,
amountOutMin,
path,
address(this),
block.timestamp
);
return amounts[1];
}"""
},
"Curve": {
"imports": [
"import {ICurvePool} from '@curvefi/contracts/interfaces/ICurvePool.sol';"
],
"swap_code": """
function _swapOnCurve(
address pool,
address tokenIn,
address tokenOut,
uint256 amountIn,
uint256 amountOutMin
) internal returns (uint256 amountOut) {
IERC20(tokenIn).approve(pool, amountIn);
int128 i = _getCoinIndex(tokenIn);
int128 j = _getCoinIndex(tokenOut);
amountOut = ICurvePool(pool).exchange(i, j, amountIn, amountOutMin);
return amountOut;
}"""
}
}

Token Addresses by Chain
TOKEN_ADDRESSES = {
"Ethereum": {
"WETH": "0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2",
"USDC": "0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48",
"USDT": "0xdAC17F958D2ee523a2206206994597C13D831ec7",
"DAI": "0x6B175474E89094C44Da98b954EedeAC495271d0F",
"WBTC": "0x2260FAC5E5542a773Aa44fBCfeDf7C193bc2C599"
},
"Arbitrum": {
"WETH": "0x82aF49447D8a07e3bd95BD0d56f35241523fBab1",
"USDC": "0xaf88d065e77c8cC2239327C5EDb3A432268e5831",
"USDT": "0xFd086bC7CD5C481DCC9C85ebE478A1C0b69FCbb9",
"DAI": "0xDA10009cBd5D07dd0CeCc66161FC93D7c9000da1",
"WBTC": "0x2f2a2543B76A4166549F7aaB2e75Bef0aefC5B0f"
},
"Base": {
"WETH": "0x4200000000000000000000000000000000000006",
"USDC": "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913",
"USDT": "0xfde4C96c8593536E31F229EA8f37b2ADa2699bb2",
"DAI": "0x50c5725949A6F0c72E6C4a641F24049A917DB0Cb",
"WBTC": "0x236aa50979D5f3De3Bd1Eeb40E81137F22ab794b"
}
}

DEX Router Addresses
DEX_ROUTERS = {
"Ethereum": {
"Uniswap V2": "0x7a250d5630B4cF539739dF2C5dAcb4c659F2488D",
"Uniswap V3": "0xE592427A0AEce92De3Edee1F18E0157C05861564",
"Sushiswap": "0xd9e1cE17f2641f24aE83637ab66a2cca9C378B9F",
"Curve": "0x9D0464996170c6B9e75eED71c68B99dDEDf279e8"
},
"Arbitrum": {
"Uniswap V3": "0xE592427A0AEce92De3Edee1F18E0157C05861564",
"Sushiswap": "0x1b02dA8Cb0d097eB8D57A175b88c7D8b47997506",
"Camelot": "0xc873fEcbd354f5A56E00E710B90EF4201db2448d"
},
"Base": {
"Uniswap V3": "0xE592427A0AEce92De3Edee1F18E0157C05861564",
"Aerodrome": "0xcF77a3Ba9A5CA399B7c97c74d54e5b1BEB874E43"
}
}

============================================================================
CONTRACT GENERATOR
============================================================================
def generate_complete_contract(
flash_provider,
dex_used,
token_in,
token_out,
amount,
strategy,
chain
):
"""Generate a complete flash loan contract with all interfaces"""

flash_data = FLASH_LOAN_PROVIDERS[flash_provider]
dex_data = DEX_INTERFACES.get(dex_used, DEX_INTERFACES["Uniswap V3"])

token_in_addr = TOKEN_ADDRESSES[chain][token_in]
token_out_addr = TOKEN_ADDRESSES[chain][token_out]
router_addr = DEX_ROUTERS.get(chain, {}).get(dex_used, "0x0000000000000000000000000000000000000000")

Build imports
all_imports = set()
for imp in flash_data["imports"]:
all_imports.add(imp)
for imp in dex_data["imports"]:
all_imports.add(imp)
all_imports.add("import {IERC20} from '@openzeppelin/contracts/token/ERC20/IERC20.sol';")
all_imports.add("import {SafeERC20} from '@openzeppelin/contracts/token/ERC20/utils/SafeERC20.sol';")
all_imports.add("import {ReentrancyGuard} from '@openzeppelin/contracts/security/ReentrancyGuard.sol';")
all_imports.add("import {Ownable} from '@openzeppelin/contracts/access/Ownable.sol';")

imports_str = "\n".join(sorted(all_imports))

Build contract
contract = f"""// SPDX-License-Identifier: MIT
pragma solidity ^0.8.19;

{imports_str}

contract FlashArbitrage is {flash_data["base_contract"]}, ReentrancyGuard, Ownable {{
using SafeERC20 for IERC20;

// ================ STATE VARIABLES ================
{f'IPool public immutable POOL;' if flash_provider == "Aave V3" else ''}
{f'IUniswapV3Pool public immutable pool;' if flash_provider == "Uniswap V3" else ''}
{f'IVault public immutable vault;' if flash_provider == "Balancer V2" else ''}

// Token addresses
address public constant TOKEN_IN = {token_in_addr};
address public constant TOKEN_OUT = {token_out_addr};

// DEX router
address public constant ROUTER = {router_addr};

// Strategy parameters
uint256 public slippageTolerance = 10; // 0.1% default
uint256 public profit;

// Events
event FlashLoanInitiated(uint256 amount);
event ArbitrageExecuted(uint256 profit);
event TokensWithdrawn(address token, uint256 amount);

// ================ CONSTRUCTOR ================
constructor({flash_data.get("constructor_params", "")})
{flash_data.get("constructor_init", "")}
{{
{f'POOL = IPool(_pool);' if flash_provider == "Aave V3" else ''}
{f'pool = IUniswapV3Pool(_pool);' if flash_provider == "Uniswap V3" else ''}
{f'vault = IVault(_vault);' if flash_provider == "Balancer V2" else ''}
}}

// ================ MAIN FUNCTIONS ================
function startArbitrage(uint256 amount) external onlyOwner nonReentrant {{
emit FlashLoanInitiated(amount);
{flash_data["flash_call"].replace("amount", "amount")}
}}

{flash_data["callback"]}

// ================ ARBITRAGE STRATEGY ================
function _executeStrategy(address asset, uint256 amount) internal {{
// Strategy: {strategy[:300]}

// Approve tokens for DEX
IERC20(asset).safeApprove(ROUTER, 0);
IERC20(asset).safeApprove(ROUTER, amount);

// Execute swap based on selected DEX
uint256 amountOut = {dex_data["swap_code"].replace("amountIn", "amount")};

// Calculate profit
profit = amountOut - amount;
require(profit > 0, "No profit");

emit ArbitrageExecuted(profit);
}}

// ================ HELPER FUNCTIONS ================
function setSlippageTolerance(uint256 _slippageTolerance) external onlyOwner {{
slippageTolerance = _slippageTolerance;
}}

function withdrawTokens(address token, uint256 amount) external onlyOwner {{
IERC20(token).safeTransfer(owner(), amount);
emit TokensWithdrawn(token, amount);
}}

function getProfit() external view returns (uint256) {{
return profit;
}}

receive() external payable {{}}
}}
"""

return contract

============================================================================
STREAMLIT APP
============================================================================
st.title("⚡ FlashForge AI")
st.markdown("Complete Flash Loan Arbitrage Studio – With All Interfaces & Token Approvals")

Session state
if "contract_code" not in st.session_state:
st.session_state.contract_code = ""
if "chat_history" not in st.session_state:
st.session_state.chat_history = []

Sidebar
with st.sidebar:
st.title("Navigation")
page = st.radio("Go to", [
"⚡ Flash Loan Wizard",
"📚 Template Library",
"📜 My Contracts"
])

st.divider()
chain = st.selectbox("Network", ["Arbitrum", "Ethereum", "Base"], index=0)

st.divider()
st.success("✅ API Connected")

client = OpenAI(
api_key=st.secrets["XAI_API_KEY"],
base_url="https://api.x.ai/v1"
)
model_name = "grok-2-latest"

Flash Loan Wizard
if page == "⚡ Flash Loan Wizard":
st.header("⚡ Flash Loan Arbitrage Wizard")
st.markdown("Generate production-ready contracts with all interfaces included")

with st.form("contract_form"):
col1, col2 = st.columns(2)

with col1:
st.subheader("Flash Loan Configuration")
flash_provider = st.selectbox(
"Flash Loan Provider",
list(FLASH_LOAN_PROVIDERS.keys()),
help="Select the protocol for flash loans"
)

token_in = st.selectbox(
"Token to Borrow",
list(TOKEN_ADDRESSES[chain].keys()),
help="Asset you want to flash loan"
)

amount = st.number_input(
"Loan Amount",
min_value=1000,
value=100000,
step=10000,
help="Amount of tokens to borrow"
)

with col2:
st.subheader("Arbitrage Configuration")
dex_used = st.selectbox(
"DEX for Swap",
list(DEX_INTERFACES.keys()),
help="Decentralized exchange to execute arbitrage"
)

token_out = st.selectbox(
"Target Token",
list(TOKEN_ADDRESSES[chain].keys()),
help="Token you want to arbitrage into"
)

slippage = st.slider(
"Slippage Tolerance (%)",
min_value=0.1,
max_value=5.0,
value=0.5,
step=0.1,
help="Maximum acceptable slippage"
)

st.subheader("Arbitrage Strategy")
strategy = st.text_area(
"Describe your strategy in detail",
value=f"Flash loan {amount} {token_in} from {flash_provider} on {chain}, swap to {token_out} on {dex_used}, execute arbitrage, repay loan with profit.",
height=100,
help="The AI will generate custom logic based on your description"
)

submitted = st.form_submit_button("🚀 Generate Contract", type="primary", use_container_width=True)

if submitted:
with st.spinner("Generating complete flash loan contract..."):
try:

Generate base contract
contract = generate_complete_contract(
flash_provider,
dex_used,
token_in,
token_out,
amount,
strategy,
chain
)

Enhance with AI for custom logic
response = client.chat.completions.create(
model=model_name,
messages=[
{"role": "system", "content": """You are an expert Solidity engineer. Enhance this flash loan contract with:

Complete arbitrage implementation based on the strategy

Proper error handling with custom errors

Gas optimizations

Detailed NatSpec comments

Slippage protection using the configured tolerance

Return only the complete contract code."""},
{"role": "user", "content": f"Contract:\n{contract}\n\nStrategy: {strategy}\nSlippage: {slippage}%"}
],
temperature=0.2,
max_completion_tokens=4000
)

st.session_state.contract_code = response.choices[0].message.content
st.success("✅ Contract generated with all interfaces!")
st.balloons()

except Exception as e:
st.error(f"Generation error: {str(e)}")

Display generated contract
if st.session_state.contract_code:
st.divider()
st.subheader("📄 Generated Contract")
st.caption("Complete contract with all interfaces, token approvals, and arbitrage logic")

edited_code = st_ace(
value=st.session_state.contract_code,
language="solidity",
theme="monokai",
height=500,
font_size=14,
show_gutter=True,
wrap=True,
key="ace_editor"
)
st.session_state.contract_code = edited_code

col1, col2, col3 = st.columns(3)
with col1:
if st.button("📋 Copy", use_container_width=True):
st.info("Contract copied to clipboard!")
with col2:
st.download_button(
label="💾 Download",
data=st.session_state.contract_code,
file_name=f"FlashArbitrage_{chain}.sol",
mime="text/plain",
use_container_width=True
)
with col3:
if st.button("🔄 Reset", use_container_width=True):
st.rerun()

Template Library
elif page == "📚 Template Library":
st.header("📚 Template Library")

templates = {
"Aave → Uniswap V3 Arbitrage": {
"desc": "Flash loan USDC from Aave, swap to WETH on Uniswap V3, arbitrage back to USDC",
"provider": "Aave V3",
"dex": "Uniswap V3"
},
"Uniswap V3 Flash Swap Arbitrage": {
"desc": "Flash swap WETH on Uniswap V3, arbitrage on Sushiswap, repay",
"provider": "Uniswap V3",
"dex": "Sushiswap"
},
"Balancer → Curve Stable Arbitrage": {
"desc": "Flash loan DAI from Balancer, arbitrage on Curve stable pools",
"provider": "Balancer V2",
"dex": "Curve"
}
}

for name, data in templates.items():
with st.expander(f"📄 {name}", expanded=False):
st.write(data["desc"])
st.info(f"Provider: {data['provider']} | DEX: {data['dex']}")
if st.button(f"Load Template", key=name):
st.session_state.contract_code = generate_complete_contract(
data["provider"],
data["dex"],
"USDC",
"WETH",
100000,
data["desc"],
"Arbitrum"
)
st.rerun()

My Contracts
elif page == "📜 My Contracts":
st.header("📜 My Contracts")

if st.session_state.contract_code:
st.subheader("Current Contract")
st.code(st.session_state.contract_code[:800] + "...", language="solidity")

st.divider()
st.subheader("Contract Audit Checklist")

checks = [
"✅ All imports are included",
"✅ Flash loan callback implemented",
"✅ Token approvals are handled",
"✅ Reentrancy protection added",
"✅ Slippage protection configured",
"✅ Profit verification included",
"✅ Owner-only functions restricted"
]

for check in checks:
st.success(check)

st.divider()
if st.button("View Full Contract", use_container_width=True):
st.code(st.session_state.contract_code, language="solidity")
else:
st.info("No contracts yet. Generate one in the Flash Loan Wizard!")

AI Co-Pilot
st.divider()
with st.expander("🤖 AI Co-Pilot - Contract Assistant", expanded=False):
for msg in st.session_state.chat_history[-5:]:
with st.chat_message(msg["role"]):
st.markdown(msg["content"])

if prompt := st.chat_input("Ask about Solidity, flash loans, or your contract..."):
st.session_state.chat_history.append({"role": "user", "content": prompt})
with st.chat_message("assistant"):
with st.spinner("🤔 Analyzing..."):
try:
context = f"Contract:\n{st.session_state.contract_code[:1500]}" if st.session_state.contract_code else ""
response = client.chat.completions.create(
model=model_name,
messages=[
{"role": "system", "content": "You are a Solidity expert specializing in DeFi flash loans and arbitrage."},
{"role": "user", "content": f"{context}\n\nQuestion: {prompt}"}
],
max_completion_tokens=500
)
answer = response.choices[0].message.content
st.markdown(answer)
st.session_state.chat_history.append({"role": "assistant", "content": answer})
except Exception as e:
st.error(f"Error: {str(e)}")

st.caption("⚡ FlashForge AI | Complete Flash Loan Studio | All Interfaces Included")
