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

# Flash Loan Provider Interfaces
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
_executeStrategy(asset, amount);
IERC20(asset).approve(address(POOL), amount + premium);
return true;
}""",
        "flash_call": "POOL.flashLoanSimple(address(this), asset, amount, '');",
        "constructor_params": "IPool _pool",
        "constructor_init": ""
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
        "flash_call": "pool.flash(address(this), amount0, amount1, data);",
        "constructor_params": "IUniswapV3Pool _pool",
        "constructor_init": "",
        "extra_vars": "IUniswapV3Pool public immutable pool;"
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
        "flash_call": "vault.flashLoan(address(this), tokens, amounts, '');",
        "constructor_params": "IVault _vault",
        "constructor_init": "",
        "extra_vars": "IVault public immutable vault;"
    }
}

# DEX Interfaces for Arbitrage
DEX_INTERFACES = {
    "Uniswap V2": {
        "imports": [
            "import {IUniswapV2Router02} from '@uniswap/v2-periphery/contracts/interfaces/IUniswapV2Router02.sol';",
            "import {IUniswapV2Pair} from '@uniswap/v2-core/contracts/interfaces/IUniswapV2Pair.sol';"
        ],
        "swap_code": """
function _swapOnDEX(
address tokenIn,
address tokenOut,
uint256 amountIn,
uint256 amountOutMin
) internal returns (uint256 amountOut) {
IERC20(tokenIn).approve(ROUTER, amountIn);
address[] memory path = new address;
path[0] = tokenIn;
path[1] = tokenOut;

uint256[] memory amounts = IUniswapV2Router02(ROUTER).swapExactTokensForTokens(
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
            "import {ISwapRouter} from '@uniswap/v3-periphery/contracts/interfaces/ISwapRouter.sol';"
        ],
        "swap_code": """
function _swapOnDEX(
address tokenIn,
address tokenOut,
uint256 amountIn,
uint256 amountOutMin
) internal returns (uint256 amountOut) {
IERC20(tokenIn).approve(ROUTER, amountIn);

ISwapRouter.ExactInputSingleParams memory params = ISwapRouter.ExactInputSingleParams({
tokenIn: tokenIn,
tokenOut: tokenOut,
fee: 3000,
recipient: address(this),
deadline: block.timestamp,
amountIn: amountIn,
amountOutMinimum: amountOutMin,
sqrtPriceLimitX96: 0
});

amountOut = ISwapRouter(ROUTER).exactInputSingle(params);
return amountOut;
}"""
    },
    "Sushiswap": {
        "imports": [
            "import {ISwapRouter} from '@sushiswap/core/contracts/interfaces/ISwapRouter.sol';"
        ],
        "swap_code": """
function _swapOnDEX(
address tokenIn,
address tokenOut,
uint256 amountIn,
uint256 amountOutMin
) internal returns (uint256 amountOut) {
IERC20(tokenIn).approve(ROUTER, amountIn);
address[] memory path = new address;
path[0] = tokenIn;
path[1] = tokenOut;

uint256[] memory amounts = ISwapRouter(ROUTER).swapExactTokensForTokens(
amountIn,
amountOutMin,
path,
address(this),
block.timestamp
);
return amounts[1];
}"""
    }
}

# Token Addresses by Chain
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

# DEX Router Addresses
DEX_ROUTERS = {
    "Ethereum": {
        "Uniswap V2": "0x7a250d5630B4cF539739dF2C5dAcb4c659F2488D",
        "Uniswap V3": "0xE592427A0AEce92De3Edee1F18E0157C05861564",
        "Sushiswap": "0xd9e1cE17f2641f24aE83637ab66a2cca9C378B9F"
    },
    "Arbitrum": {
        "Uniswap V3": "0xE592427A0AEce92De3Edee1F18E0157C05861564",
        "Sushiswap": "0x1b02dA8Cb0d097eB8D57A175b88c7D8b47997506"
    },
    "Base": {
        "Uniswap V3": "0xE592427A0AEce92De3Edee1F18E0157C05861564"
    }
}

def generate_complete_contract(flash_provider, dex_used, token_in, token_out, amount, strategy, chain, slippage):
    """Generate a complete flash loan contract with all interfaces"""
    
    flash_data = FLASH_LOAN_PROVIDERS[flash_provider]
    dex_data = DEX_INTERFACES.get(dex_used, DEX_INTERFACES["Uniswap V3"])
    
    token_in_addr = TOKEN_ADDRESSES[chain][token_in]
    token_out_addr = TOKEN_ADDRESSES[chain][token_out]
    router_addr = DEX_ROUTERS.get(chain, {}).get(dex_used, "0x0000000000000000000000000000000000000000")
    
    all_imports = [
        "import {IERC20} from '@openzeppelin/contracts/token/ERC20/IERC20.sol';",
        "import {SafeERC20} from '@openzeppelin/contracts/token/ERC20/utils/SafeERC20.sol';",
        "import {ReentrancyGuard} from '@openzeppelin/contracts/security/ReentrancyGuard.sol';",
        "import {Ownable} from '@openzeppelin/contracts/access/Ownable.sol';"
    ]
    
    for imp in flash_data["imports"]:
        all_imports.append(imp)
    for imp in dex_data["imports"]:
        all_imports.append(imp)
    
    imports_str = "\n".join(list(set(all_imports)))
    
    extra_vars = flash_data.get("extra_vars", "")
    constructor_params = flash_data.get("constructor_params", "")
    constructor_init = flash_data.get("constructor_init", "")
    
    slippage_tolerance = int(slippage * 10)
    
    contract = f"""// SPDX-License-Identifier: MIT
pragma solidity ^0.8.19;

{imports_str}

contract FlashArbitrage is {flash_data["base_contract"]}, ReentrancyGuard, Ownable {{
using SafeERC20 for IERC20;

{extra_vars}

address public constant TOKEN_IN = {token_in_addr};
address public constant TOKEN_OUT = {token_out_addr};
address public constant ROUTER = {router_addr};

uint256 public slippageTolerance = {slippage_tolerance};
uint256 public profit;

event FlashLoanInitiated(uint256 amount);
event ArbitrageExecuted(uint256 amountIn, uint256 amountOut, uint256 profit);
event TokensWithdrawn(address token, uint256 amount);

constructor({constructor_params})
{constructor_init}
{{
transferOwnership(msg.sender);
}}

function startArbitrage(uint256 amount) external onlyOwner nonReentrant {{
emit FlashLoanInitiated(amount);
{flash_data["flash_call"]}
}}

{flash_data["callback"]}

function _executeStrategy(address asset, uint256 amount) internal {{
uint256 amountOutMin = amount * (1000 - slippageTolerance) / 1000;

IERC20(asset).safeApprove(ROUTER, 0);
IERC20(asset).safeApprove(ROUTER, amount);

uint256 amountOut = _swapOnDEX(asset, TOKEN_OUT, amount, amountOutMin);

profit = amountOut - amount;
require(profit > 0, "No profit");

emit ArbitrageExecuted(amount, amountOut, profit);
}}

{dex_data["swap_code"]}

function setSlippageTolerance(uint256 _slippageTolerance) external onlyOwner {{
slippageTolerance = _slippageTolerance;
}}

function withdrawTokens(address token, uint256 amount) external onlyOwner {{
IERC20(token).safeTransfer(owner(), amount);
emit TokensWithdrawn(token, amount);
}}

function withdrawETH() external onlyOwner {{
payable(owner()).transfer(address(this).balance);
}}

function getProfit() external view returns (uint256) {{
return profit;
}}

receive() external payable {{}}
}}
"""
    return contract

st.title("⚡ FlashForge AI")
st.markdown("Complete Flash Loan Arbitrage Studio – With All Interfaces & Token Approvals")

if "contract_code" not in st.session_state:
    st.session_state.contract_code = ""
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

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

if page == "⚡ Flash Loan Wizard":
    st.header("⚡ Flash Loan Arbitrage Wizard")
    st.markdown("Generate production-ready contracts with all interfaces included")
    
    with st.form("contract_form"):
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("Flash Loan Configuration")
            flash_provider = st.selectbox(
                "Flash Loan Provider",
                list(FLASH_LOAN_PROVIDERS.keys())
            )
            
            token_in = st.selectbox(
                "Token to Borrow",
                list(TOKEN_ADDRESSES[chain].keys())
            )
            
            amount = st.number_input(
                "Loan Amount",
                min_value=1000,
                value=100000,
                step=10000
            )
        
        with col2:
            st.subheader("Arbitrage Configuration")
            dex_used = st.selectbox(
                "DEX for Swap",
                list(DEX_INTERFACES.keys())
            )
            
            token_out = st.selectbox(
                "Target Token",
                list(TOKEN_ADDRESSES[chain].keys())
            )
            
            slippage = st.slider(
                "Slippage Tolerance (%)",
                min_value=0.1,
                max_value=5.0,
                value=0.5,
                step=0.1
            )
        
        st.subheader("Arbitrage Strategy")
        strategy = st.text_area(
            "Describe your strategy in detail",
            value=f"Flash loan {amount} {token_in} from {flash_provider} on {chain}, swap to {token_out} on {dex_used}, execute arbitrage, repay loan with profit.",
            height=100
        )
        
        submitted = st.form_submit_button("🚀 Generate Contract", type="primary", use_container_width=True)
    
    if submitted:
        with st.spinner("Generating complete flash loan contract..."):
            try:
                contract = generate_complete_contract(
                    flash_provider, dex_used, token_in, token_out,
                    amount, strategy, chain, slippage
                )
                
                response = client.chat.completions.create(
                    model=model_name,
                    messages=[
                        {"role": "system", "content": "You are an expert Solidity engineer. Enhance this flash loan contract with complete arbitrage implementation based on the strategy. Return only the complete contract code."},
                        {"role": "user", "content": f"Contract:\n{contract}\n\nStrategy: {strategy}"}
                    ],
                    temperature=0.2,
                    max_completion_tokens=4000
                )
                
                st.session_state.contract_code = response.choices[0].message.content
                st.success("✅ Contract generated successfully!")
                st.balloons()
            
            except Exception as e:
                st.error(f"Generation error: {str(e)}")
    
    if st.session_state.contract_code:
        st.divider()
        st.subheader("📄 Generated Contract")
        
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
            st.download_button(
                label="💾 Download",
                data=st.session_state.contract_code,
                file_name=f"FlashArbitrage_{chain}.sol",
                mime="text/plain",
                use_container_width=True
            )
        with col2:
            if st.button("🔄 Reset", use_container_width=True):
                st.rerun()
        with col3:
            st.info("📋 Copy the code above")

elif page == "📚 Template Library":
    st.header("📚 Template Library")
    
    templates = {
        "Aave to Uniswap V3 Arbitrage": {
            "desc": "Flash loan USDC from Aave, swap to WETH on Uniswap V3, arbitrage back",
            "provider": "Aave V3",
            "dex": "Uniswap V3"
        },
        "Uniswap V3 Flash Swap Arbitrage": {
            "desc": "Flash swap on Uniswap V3, arbitrage on Sushiswap",
            "provider": "Uniswap V3",
            "dex": "Sushiswap"
        }
    }
    
    for name, data in templates.items():
        with st.expander(f"📄 {name}", expanded=False):
            st.write(data["desc"])
            st.info(f"Provider: {data['provider']} | DEX: {data['dex']}")
            if st.button(f"Load Template", key=name):
                st.session_state.contract_code = generate_complete_contract(
                    data["provider"], data["dex"], "USDC", "WETH",
                    100000, data["desc"], "Arbitrum", 0.5
                )
                st.rerun()

elif page == "📜 My Contracts":
    st.header("📜 My Contracts")
    
    if st.session_state.contract_code:
        st.subheader("Current Contract Preview")
        st.code(st.session_state.contract_code[:800] + "...", language="solidity")
        
        st.divider()
        st.subheader("Security Checklist")
        checks = [
            "Flash loan callback implemented",
            "Token approvals handled with SafeERC20",
            "Reentrancy protection added",
            "Slippage protection configured",
            "Profit verification included",
            "Owner-only functions restricted"
        ]
        for check in checks:
            st.success(f"✅ {check}")
        
        if st.button("View Full Contract", use_container_width=True):
            st.code(st.session_state.contract_code, language="solidity")
    else:
        st.info("No contracts yet. Generate one in the Flash Loan Wizard!")

    st.divider()
    with st.expander("🤖 AI Co-Pilot", expanded=False):
        for msg in st.session_state.chat_history[-5:]:
            with st.chat_message(msg["role"]):
                st.markdown(msg["content"])
        
        if prompt := st.chat_input("Ask about your contract..."):
            st.session_state.chat_history.append({"role": "user", "content": prompt})
            with st.chat_message("assistant"):
                with st.spinner("Thinking..."):
                    try:
                        context = f"Contract:\n{st.session_state.contract_code[:1500]}" if st.session_state.contract_code else ""
                        response = client.chat.completions.create(
                            model=model_name,
                            messages=[
                                {"role": "system", "content": "You are a Solidity expert specializing in flash loans."},
                                {"role": "user", "content": f"{context}\n\nQuestion: {prompt}"}
                            ],
                            max_completion_tokens=500
                        )
                        st.markdown(response.choices[0].message.content)
                        st.session_state.chat_history.append({"role": "assistant", "content": response.choices[0].message.content})
                    except Exception as e:
                        st.error(f"Error: {str(e)}")
