
import streamlit as st
from openai import OpenAI
from streamlit_ace import st_ace

st.set_page_config(page_title="FlashForge AI ⚡", page_icon="⚡", layout="wide")

# ====================== SECRET CHECK ======================
if "XAI_API_KEY" not in st.secrets or not st.secrets["XAI_API_KEY"]:
    st.error("🔑 **XAI_API_KEY is missing**", icon="🚨")
    st.markdown("""
    ### How to fix it (takes 20 seconds):
    1. In the top-right corner of this app → click **⋮** → **Settings**
    2. Left sidebar → click **Secrets**
    3. Paste this into the big box:

    ```toml
    XAI_API_KEY = "xai-XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX"
Click Save

Refresh this page
""")
st.stop()

====================== FLASH LOAN INTERFACES LIBRARY ======================
FLASH_LOAN_INTERFACES = {
"Aave V3 (0.09%)": {
"name": "Aave V3",
"imports": """import {FlashLoanSimpleReceiverBase} from "@aave/core-v3/contracts/flashloan/base/FlashLoanSimpleReceiverBase.sol";
import {IPoolAddressesProvider} from "@aave/core-v3/contracts/interfaces/IPoolAddressesProvider.sol";
import {IERC20} from "@openzeppelin/contracts/token/ERC20/IERC20.sol";
import {SafeERC20} from "@openzeppelin/contracts/token/ERC20/utils/SafeERC20.sol";""",
"base_contract": "FlashLoanSimpleReceiverBase",
"callback": """
function executeOperation(
address asset,
uint256 amount,
uint256 premium,
address initiator,
bytes calldata params
) external override returns (bool) {
// Execute your arbitrage strategy
_executeStrategy(amount, asset);

// Approve repayment
IERC20(asset).approve(address(POOL), amount + premium);
return true;
}""",
"flash_call": """
POOL.flashLoanSimple(address(this), ASSET, amount, "");""",
"constructor_params": "IPoolAddressesProvider _addressesProvider",
"constructor_init": "FlashLoanSimpleReceiverBase(_addressesProvider)"
},

"Uniswap V3 Flash Swap (0%)": {
"name": "Uniswap V3",
"imports": """import {IUniswapV3Pool} from "@uniswap/v3-core/contracts/interfaces/IUniswapV3Pool.sol";
import {IERC20} from "@openzeppelin/contracts/token/ERC20/IERC20.sol";
import {SafeERC20} from "@openzeppelin/contracts/token/ERC20/utils/SafeERC20.sol";
import {IUniswapV3SwapCallback} from "@uniswap/v3-core/contracts/interfaces/callback/IUniswapV3SwapCallback.sol";
import {TransferHelper} from "@uniswap/v3-periphery/contracts/libraries/TransferHelper.sol";""",
"base_contract": "IUniswapV3SwapCallback",
"callback": """
function uniswapV3SwapCallback(
int256 amount0Delta,
int256 amount1Delta,
bytes calldata data
) external override {
// Determine which token was borrowed
if (amount0Delta > 0) {
TransferHelper.safeTransfer(address(pool.token0()), msg.sender, uint256(amount0Delta));
} else if (amount1Delta > 0) {
TransferHelper.safeTransfer(address(pool.token1()), msg.sender, uint256(amount1Delta));
}
}""",
"flash_call": """
pool.flash(address(this), amount, 0, abi.encode(address(this)));""",
"constructor_params": "address _pool",
"constructor_init": ""
},

"Balancer V2": {
"name": "Balancer V2",
"imports": """import {IERC20} from "@openzeppelin/contracts/token/ERC20/IERC20.sol";
import {SafeERC20} from "@openzeppelin/contracts/token/ERC20/utils/SafeERC20.sol";
import {IVault} from "@balancer-labs/v2-interfaces/contracts/vault/IVault.sol";
import {IFlashLoanRecipient} from "@balancer-labs/v2-interfaces/contracts/vault/IFlashLoanRecipient.sol";""",
"base_contract": "IFlashLoanRecipient",
"callback": """
function receiveFlashLoan(
IERC20[] memory tokens,
uint256[] memory amounts,
uint256[] memory feeAmounts,
bytes memory userData
) external override {
require(msg.sender == address(VAULT), "Not vault");

// Execute strategy
_executeStrategy(amounts[0], address(tokens[0]));

// Approve repayment
tokens[0].approve(address(VAULT), amounts[0] + feeAmounts[0]);
}""",
"flash_call": """
IERC20[] memory tokens = new IERC20;
tokens[0] = IERC20(ASSET);
uint256[] memory amounts = new uint256;
amounts[0] = amount;
VAULT.flashLoan(address(this), tokens, amounts, "");""",
"constructor_params": "address _vault",
"constructor_init": ""
},

"Morpho": {
"name": "Morpho",
"imports": """import {IMorpho} from "@morpho-blue/interfaces/IMorpho.sol";
import {IERC20} from "@openzeppelin/contracts/token/ERC20/IERC20.sol";
import {SafeERC20} from "@openzeppelin/contracts/token/ERC20/utils/SafeERC20.sol";""",
"base_contract": "",
"callback": """
function onMorphoFlashLoan(
uint256 amount,
uint256 fee,
bytes calldata data
) external override {
require(msg.sender == address(MORPHO), "Not morpho");

// Execute strategy
_executeStrategy(amount, address(ASSET));

// Approve repayment
IERC20(ASSET).approve(address(MORPHO), amount + fee);
}""",
"flash_call": """
MORPHO.flashLoan(address(this), ASSET, amount, "");""",
"constructor_params": "address _morpho",
"constructor_init": ""
}
}

====================== CHAIN ADDRESSES ======================
CHAIN_ADDRESSES = {
"Ethereum": {
"USDC": "0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48",
"WETH": "0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2",
"WBTC": "0x2260FAC5E5542a773Aa44fBCfeDf7C193bc2C599",
"DAI": "0x6B175474E89094C44Da98b954EedeAC495271d0F"
},
"Arbitrum": {
"USDC": "0xaf88d065e77c8cC2239327C5EDb3A432268e5831",
"WETH": "0x82aF49447D8a07e3bd95BD0d56f35241523fBab1",
"WBTC": "0x2f2a2543B76A4166549F7aaB2e75Bef0aefC5B0f",
"DAI": "0xDA10009cBd5D07dd0CeCc66161FC93D7c9000da1"
},
"Base": {
"USDC": "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913",
"WETH": "0x4200000000000000000000000000000000000006",
"WBTC": "0x236aa50979D5f3De3Bd1Eeb40E81137F22ab794b",
"DAI": "0x50c5725949A6F0c72E6C4a641F24049A917DB0Cb"
},
"Optimism": {
"USDC": "0x0b2C639c533813f4Aa9D7837CAf62653d097Ff85",
"WETH": "0x4200000000000000000000000000000000000006",
"WBTC": "0x68f180fcCe6836688e9084f035309E29Bf0A2095",
"DAI": "0xDA10009cBd5D07dd0CeCc66161FC93D7c9000da1"
},
"Polygon": {
"USDC": "0x2791Bca1f2de4661ED88A30C99A7a9449Aa84174",
"WETH": "0x7ceB23fD6bC0adD59E62ac25578270cFf1b9f619",
"WBTC": "0x1bfd67037b42cf73acF2047067bd4F2C47D9BfD6",
"DAI": "0x8f3Cf7ad23Cd3CaDbD9735AFf958023239c6A063"
}
}

====================== CONTRACT GENERATOR ======================
def generate_contract(provider, asset, amount, strategy, chain):
"""Generate complete flash loan contract with all interfaces"""

interface = FLASH_LOAN_INTERFACES[provider]
token_address = CHAIN_ADDRESSES[chain][asset]

contract = f"""// SPDX-License-Identifier: MIT
pragma solidity ^0.8.28;

{interface["imports"]}

contract FlashArbitrage is {interface["base_contract"]} {{
using SafeERC20 for IERC20;

// ================ CONSTANTS ================
address public constant ASSET = {token_address}; // {asset} on {chain}

// ================ STATE VARIABLES ================
{f'IPoolAddressesProvider public immutable ADDRESSES_PROVIDER;' if provider == "Aave V3 (0.09%)" else ''}
{f'IUniswapV3Pool public immutable pool;' if provider == "Uniswap V3 Flash Swap (0%)" else ''}
{f'IVault public immutable VAULT;' if provider == "Balancer V2" else ''}
{f'IMorpho public immutable MORPHO;' if provider == "Morpho" else ''}

address public owner;
uint256 public profit;

// ================ EVENTS ================
event FlashLoanExecuted(uint256 amount, uint256 profit);
event ArbitrageExecuted(uint256 amountIn, uint256 amountOut);

// ================ MODIFIERS ================
modifier onlyOwner() {{
require(msg.sender == owner, "Not owner");
_;
}}

// ================ CONSTRUCTOR ================
constructor({interface["constructor_params"]})
{interface["constructor_init"]}
{{
owner = msg.sender;
{f'ADDRESSES_PROVIDER = _addressesProvider;' if provider == "Aave V3 (0.09%)" else ''}
{f'pool = IUniswapV3Pool(_pool);' if provider == "Uniswap V3 Flash Swap (0%)" else ''}
{f'VAULT = IVault(_vault);' if provider == "Balancer V2" else ''}
{f'MORPHO = IMorpho(_morpho);' if provider == "Morpho" else ''}
}}

// ================ MAIN FUNCTIONS ================
function startArbitrage(uint256 amount) external onlyOwner {{
{interface["flash_call"]}
}}

{interface["callback"]}

function _executeStrategy(uint256 amount, address asset) internal {{
// Strategy: {strategy[:200]}

// TODO: Implement your custom arbitrage logic here
// Example structure:
// 1. Approve tokens for DEX
// 2. Execute swap on first DEX
// 3. Execute swap on second DEX
// 4. Calculate profit

// Placeholder profit calculation
profit = amount * 1 / 1000; // 0.1% profit example

emit ArbitrageExecuted(amount, profit);
}}

// ================ HELPER FUNCTIONS ================
function approveToken(address token, address spender, uint256 amount) internal {{
IERC20(token).safeApprove(spender, 0);
IERC20(token).safeApprove(spender, amount);
}}

function withdrawTokens(address token, uint256 amount) external onlyOwner {{
IERC20(token).safeTransfer(owner, amount);
}}

function withdrawETH() external onlyOwner {{
payable(owner).transfer(address(this).balance);
}}

// ================ VIEW FUNCTIONS ================
function getProfit() external view returns (uint256) {{
return profit;
}}

receive() external payable {{}}
}}
"""
return contract

def enhance_with_ai(base_contract, strategy, chain, provider, asset, amount, client, model_name):
"""Use AI to add custom arbitrage logic to the contract"""

system_prompt = f"""You are an expert Solidity engineer specializing in DeFi arbitrage and flash loans.
Enhance the provided flash loan contract with specific arbitrage logic.

Requirements:

Add complete arbitrage implementation based on the strategy

Include proper slippage protection (default 0.1%)

Add gas optimizations

Include detailed NatSpec comments

Add error handling with custom errors

Ensure all token approvals are handled correctly

Return the complete enhanced contract code only, no explanations."""

user_prompt = f"""Chain: {chain}
Provider: {provider}
Asset: {asset}
Amount: {amount}
Strategy: {strategy}

Base Contract:
{base_contract}

Enhance this contract with the specific arbitrage logic described in the strategy.
Make it production-ready with all necessary safety checks."""

try:
response = client.chat.completions.create(
model=model_name,
messages=[
{"role": "system", "content": system_prompt},
{"role": "user", "content": user_prompt}
],
temperature=0.2,
max_completion_tokens=4000
)
return response.choices[0].message.content
except Exception as e:
st.error(f"AI enhancement failed: {str(e)}")
return base_contract

====================== APP UI ======================
st.title("⚡ FlashForge AI")
st.markdown("AI-Powered Solidity Flash Loan & Arbitrage Studio – Deploy in < 5 min")

Session state
if "contract_code" not in st.session_state:
st.session_state.contract_code = ""
if "chat_history" not in st.session_state:
st.session_state.chat_history = []

Sidebar
with st.sidebar:
st.title("Navigation")
page = st.radio("Go to", [
"📚 Template Library",
"⚡ Flash Loan Wizard (Main)",
"📜 My Contracts"
])

st.divider()
st.caption("Connected Chain")
chain = st.selectbox("Chain", ["Arbitrum", "Ethereum", "Base", "Optimism", "Polygon"], index=0)

st.divider()
st.success("✅ XAI API Key Connected")

Initialize OpenAI client
client = OpenAI(
api_key=st.secrets["XAI_API_KEY"],
base_url="https://api.x.ai/v1"
)
model_name = "grok-2-latest"

Template Library Page
if page == "📚 Template Library":
st.header("📚 Template Library – Quick Deploy")
st.markdown("Pre-built templates for common flash loan strategies")

col1, col2 = st.columns(2)

with col1:
with st.expander("🏦 Aave V3 - Simple Arbitrage", expanded=True):
st.code("""// Flash loan USDC from Aave V3
// Execute arbitrage between Uniswap and Sushiswap
// Repay loan with premium""", language="text")
if st.button("Load Aave Template", key="aave_template"):
st.session_state.contract_code = generate_contract(
"Aave V3 (0.09%)", "USDC", 100000,
"Simple arbitrage between Uniswap and Sushiswap", "Arbitrum"
)
st.rerun()

with col2:
with st.expander("🦄 Uniswap V3 - Flash Swap", expanded=True):
st.code("""// Flash swap on Uniswap V3
// Borrow WETH, swap to USDC on another pool
// Repay flash swap with profit""", language="text")
if st.button("Load Uniswap Template", key="uniswap_template"):
st.session_state.contract_code = generate_contract(
"Uniswap V3 Flash Swap (0%)", "WETH", 100,
"Flash swap WETH, arbitrage between Uniswap pools", "Arbitrum"
)
st.rerun()

Flash Loan Wizard Page
elif page == "⚡ Flash Loan Wizard (Main)":
st.header("⚡ Flash Loan Arbitrage Wizard")
st.markdown("Generate custom flash loan contracts with AI assistance")

col1, col2 = st.columns([1, 2])

with col1:
st.subheader("1. Configure Flash Loan")

provider = st.selectbox(
"Flash Loan Provider",
list(FLASH_LOAN_INTERFACES.keys()),
help="Select the DeFi protocol for flash loans"
)

asset = st.selectbox(
"Asset to Borrow",
["USDC", "WETH", "WBTC", "DAI"],
help="Token you want to flash loan"
)

amount = st.number_input(
"Loan Amount",
min_value=1000,
value=100000,
step=10000,
format="%d",
help="Amount of tokens to borrow"
)

st.subheader("2. Describe Arbitrage Strategy")
strategy = st.text_area(
"Natural Language Strategy",
value="Flash loan 100k USDC from Aave on Arbitrum, buy WBTC on Uniswap V3 0.3% pool, sell WBTC on Sushiswap, repay loan with 0.1% slippage tolerance.",
height=150,
help="Describe your arbitrage strategy in plain English"
)

st.info(f"💡 Provider: {FLASH_LOAN_INTERFACES[provider]['name']}\n\nChain: {chain}\n\nAsset: {asset}\n\nAmount: {amount:,}")

with col2:
st.subheader("3. Generate Contract")

if st.button("🚀 Generate Solidity Contract", type="primary", use_container_width=True):
with st.spinner("Generating flash loan contract with AI..."):
try:

Step 1: Generate base contract with interfaces
base_contract = generate_contract(provider, asset, amount, strategy, chain)

Step 2: Enhance with AI for custom logic
enhanced_contract = enhance_with_ai(
base_contract, strategy, chain, provider, asset, amount,
client, model_name
)

st.session_state.contract_code = enhanced_contract
st.success("✅ Contract generated successfully!")
st.balloons()

except Exception as e:
st.error(f"❌ Generation failed: {str(e)}")

if st.session_state.contract_code:
st.subheader("📄 Generated Contract")
st.caption("Edit the contract directly below - changes are automatically saved")

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

Action buttons
col_a, col_b, col_c = st.columns(3)
with col_a:
if st.button("📋 Copy to Clipboard", use_container_width=True):
st.write("✅ Copied! (Press Ctrl+C)")
st.code(st.session_state.contract_code, language="solidity")
with col_b:
if st.button("🔄 Reset to Generated", use_container_width=True):
st.rerun()
with col_c:
st.download_button(
label="💾 Download Contract",
data=st.session_state.contract_code,
file_name=f"FlashArbitrage_{provider.replace(' ', '')}{chain}.sol",
mime="text/plain",
use_container_width=True
)

My Contracts Page
elif page == "📜 My Contracts":
st.header("📜 My Contracts")

if st.session_state.contract_code:
st.subheader("Current Contract")
st.code(st.session_state.contract_code[:500] + "...", language="solidity")

if st.button("View Full Contract", use_container_width=True):
st.code(st.session_state.contract_code, language="solidity")

st.divider()

st.subheader("Contract Metadata")
col1, col2 = st.columns(2)
with col1:
st.metric("Lines of Code", len(st.session_state.contract_code.split('\n')))
with col2:
st.metric("File Size", f"{len(st.session_state.contract_code):,} bytes")

st.divider()

st.subheader("Deployment Checklist")
st.checkbox("✅ Imports are correct")
st.checkbox("✅ Constructor parameters are set")
st.checkbox("✅ Token addresses match target chain")
st.checkbox("✅ Slippage tolerance is set")
st.checkbox("✅ Owner address is correct")

else:
st.info("No contracts generated yet. Go to the Flash Loan Wizard to create your first contract!")

AI Co-Pilot Chat (Global)
st.divider()
with st.expander("🤖 AI Co-Pilot - Ask about your contract", expanded=False):
for msg in st.session_state.chat_history:
with st.chat_message(msg["role"]):
st.markdown(msg["content"])

if prompt := st.chat_input("Ask about Solidity, flash loans, or your contract..."):
st.session_state.chat_history.append({"role": "user", "content": prompt})
with st.chat_message("user"):
st.markdown(prompt)
with st.chat_message("assistant"):
with st.spinner("🤔 Thinking..."):
try:
context = f"Current contract:\n{st.session_state.contract_code[:2000]}\n\n" if st.session_state.contract_code else ""
response = client.chat.completions.create(
model=model_name,
messages=[
{"role": "system", "content": "You are a Solidity expert helping with flash loan contracts."},
{"role": "user", "content": context + prompt}
],
max_completion_tokens=1000
)
answer = response.choices[0].message.content
st.markdown(answer)
st.session_state.chat_history.append({"role": "assistant", "content": answer})
except Exception as e:
st.error(f"Error: {str(e)}")

Footer
st.divider()
st.caption("⚡ FlashForge AI © 2026 | AI-Powered Solidity Flash Loan Studio")
st.caption("Supported: Aave V3, Uniswap V3, Balancer V2, Morpho | Chains: Ethereum, Arbitrum, Base, Optimism, Polygon")
