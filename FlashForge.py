import streamlit as st
from openai import OpenAI
from streamlit_ace import st_ace

st.set_page_config(page_title="FlashForge AI ⚡", page_icon="⚡", layout="wide")

# ====================== SECRET CHECK (NEW SAFETY NET) ======================
if "XAI_API_KEY" not in st.secrets or not st.secrets["XAI_API_KEY"]:
    st.error("🔑 **XAI_API_KEY is missing**", icon="🚨")
    st.markdown("""
    ### How to fix it (takes 20 seconds):
    1. In the top-right corner of this app → click **⋮** → **Settings**
    2. Left sidebar → click **Secrets**
    3. Paste this into the big box:

    ```toml
    XAI_API_KEY = "xai-XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX"
    ```

    4. Click **Save**
    5. Refresh this page (or just wait 5 seconds)
    """)
    st.stop()  # stops the app until secret is set

# ====================== REST OF THE APP ======================
st.title("⚡ FlashForge AI")
st.markdown("**AI-Powered Solidity Flash Loan & Arbitrage Studio** – Deploy in < 5 min")

# Session state
if "contract_code" not in st.session_state:
    st.session_state.contract_code = ""
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

# Sidebar
with st.sidebar:
    st.title("Navigation")
    page = st.radio("Go to",
                    ["📚 Template Library",
                     "⚡ Flash Loan Wizard (Main)",
                     "🛠 Custom AI Builder",
                     "📜 My Contracts"])
   
    st.divider()
    st.caption("Connected Chain")
    chain = st.selectbox("Chain", ["Ethereum", "Arbitrum", "Base", "Optimism", "Polygon"], index=1)
   
    st.divider()
    st.success("✅ XAI API Key Connected")  # only shows after secret is set
    client = OpenAI(
        api_key=st.secrets["XAI_API_KEY"],
        base_url="https://api.x.ai/v1"
    )
    model_name = "grok-2-latest"

# (The rest of your original code stays exactly the same – templates, wizard, etc.)
# I kept everything else identical so you don't lose any functionality.
# Only the top part was changed for safety.

# ====================== TEMPLATES ======================
TEMPLATES = {
    "Simple Aave V3 Flash Loan Arbitrage": {
        "description": "Flash loan USDC → Buy WBTC on Uniswap V3 → Sell on Sushiswap → Repay",
        "code": """// SPDX-License-Identifier: MIT
pragma solidity ^0.8.28;
import "@aave/core-v3/contracts/flashloan/base/FlashLoanSimpleReceiverBase.sol";
import "@uniswap/v3-periphery/contracts/interfaces/ISwapRouter.sol";

contract FlashArbitrage is FlashLoanSimpleReceiverBase {
    ISwapRouter public immutable uniswapRouter;
    address public immutable wbtc;
    address public immutable usdc;

    function startArbitrage(uint256 amount) external {
        POOL.flashLoanSimple(address(this), usdc, amount, "");
    }
}"""
    }
}

# ====================== PAGES (unchanged) ======================
if page == "📚 Template Library":
    st.header("Template Library – Quick Deploy")
    cols = st.columns(3)
    for i, (name, data) in enumerate(TEMPLATES.items()):
        with cols[i % 3]:
            with st.expander(f"**{name}**", expanded=True):
                st.write(data["description"])
                if st.button("Quick Deploy →", key=name):
                    st.session_state.contract_code = data["code"]
                    st.rerun()

elif page == "⚡ Flash Loan Wizard (Main)":
    st.header("⚡ Flash Loan Arbitrage Wizard")
    col1, col2 = st.columns([1, 2])
    with col1:
        st.subheader("1. Provider & Loan")
        provider = st.selectbox("Flash Loan Provider", ["Aave V3 (0.09%)", "Uniswap V3 Flash Swap (0%)", "Balancer V2", "Morpho"])
        asset = st.selectbox("Asset", ["USDC", "WETH", "WBTC", "DAI"])
        amount = st.number_input("Loan Amount", value=100_000, step=10_000)
       
        st.subheader("2. Describe Your Strategy")
        user_prompt = st.text_area("Natural language",
                                   value="Flash loan 100k USDC from Aave on Arbitrum, buy WBTC on Uniswap V3 0.3% pool, sell WBTC on Sushiswap, add 50% of profit as liquidity to USDC-WBTC pool on Uniswap V3, repay loan with 0.1% slippage tolerance.",
                                   height=150)
   
    with col2:
        st.subheader("3. Generate Contract")
        if st.button("🚀 AI → Generate Full Solidity Contract", type="primary", use_container_width=True):
            with st.spinner("Grok is writing production-ready Solidity..."):
                system_prompt = """You are an expert Solidity engineer specialized in flash-loan arbitrage.
                Generate a complete, audited, gas-optimized Solidity 0.8.28 contract."""
               
                response = client.chat.completions.create(
                    model=model_name,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": f"Chain: {chain}\nProvider: {provider}\nAsset: {asset}\nAmount: {amount}\nStrategy: {user_prompt}"}
                    ],
                    temperature=0.2,
                    max_tokens=4000
                )
                st.session_state.contract_code = response.choices[0].message.content
                st.success("✅ Contract generated!")

        if st.session_state.contract_code:
            st.subheader("📄 Generated Contract")
            edited_code = st_ace(
                value=st.session_state.contract_code,
                language="solidity",
                theme="monokai",
                height=600,
                font_size=14,
                show_gutter=True,
                wrap=True,
                key="ace_editor"
            )
            st.session_state.contract_code = edited_code

# AI Co-Pilot chat (unchanged)
st.divider()
st.subheader("🤖 AI Co-Pilot Chat")
for msg in st.session_state.chat_history:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

if prompt := st.chat_input("Ask anything about your contract..."):
    st.session_state.chat_history.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)
    with st.chat_message("assistant"):
        with st.spinner("Thinking..."):
            response = client.chat.completions.create(
                model=model_name,
                messages=[{"role": m["role"], "content": m["content"]} for m in st.session_state.chat_history]
            )
            answer = response.choices[0].message.content
            st.markdown(answer)
            st.session_state.chat_history.append({"role": "assistant", "content": answer})

st.caption("FlashForge AI © 2026 | Secrets now safely checked on startup") 
