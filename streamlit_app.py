import streamlit as st
import json
from datetime import datetime
from backend import Transaction, Block, FullNode, SPVClient

# Page configuration
st.set_page_config(
    page_title="SPV Blockchain Simulator - by Abraham",
    page_icon="🔗",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for better styling
st.markdown("""
<style>
    .stTabs [data-baseweb="tab-list"] {
        gap: 24px;
    }
    .stTabs [data-baseweb="tab"] {
        height: 50px;
        padding-left: 20px;
        padding-right: 20px;
    }
    .success-box {
        padding: 20px;
        border-radius: 5px;
        background-color: #d4edda;
        border: 1px solid #c3e6cb;
        color: #155724;
    }
    .failure-box {
        padding: 20px;
        border-radius: 5px;
        background-color: #f8d7da;
        border: 1px solid #f5c6cb;
        color: #721c24;
    }
    .info-box {
        padding: 15px;
        border-radius: 5px;
        background-color: #d1ecf1;
        border: 1px solid #bee5eb;
        color: #0c5460;
    }
</style>
""", unsafe_allow_html=True)

# Initialize session state
if 'full_node' not in st.session_state:
    st.session_state.full_node = None
if 'spv_client' not in st.session_state:
    st.session_state.spv_client = SPVClient()
if 'transactions' not in st.session_state:
    st.session_state.transactions = []
if 'log_messages' not in st.session_state:
    st.session_state.log_messages = []
if 'stats' not in st.session_state:
    st.session_state.stats = {
        'total_verifications': 0,
        'successful_verifications': 0,
        'failed_verifications': 0
    }

def log_message(message):
    """Add message to log"""
    st.session_state.log_messages.append(message)

def create_block(tx_data_list):
    """Create block from transaction data"""
    st.session_state.log_messages = []  # Clear log
    log_message("--- [SETUP PHASE] ---")
    
    if not tx_data_list:
        log_message("❌ Error: No transactions entered.")
        return False
    
    log_message(f"Creating {len(tx_data_list)} Transaction objects...")
    transactions = [Transaction(data.strip()) for data in tx_data_list if data.strip()]
    
    log_message("Creating Block and building Merkle Tree...")
    block = Block(transactions)
    
    log_message("Initializing Full Node with the new block...")
    st.session_state.full_node = FullNode(block)
    st.session_state.transactions = transactions
    
    log_message("\n--- [NETWORK SIM: 'Must have 2'] ---")
    log_message("SPV Client connecting to Full Node...")
    log_message("SPV Client downloading block header... 🧠")
    
    # Set header for SPV client
    st.session_state.spv_client.block_header = block.header
    log_message("SPV Client: Downloaded and stored block header.")
    log_message(f"   > Header Merkle Root: {block.header['merkle_root'][:32]}...")
    
    # Print tree structure
    print_merkle_tree()
    
    log_message("\n✅ Setup complete. Ready to verify transactions.")
    return True

def print_merkle_tree():
    """Print Merkle tree structure to log"""
    if not st.session_state.full_node:
        return
    
    log_message("\n--- [MERKLE TREE STRUCTURE] ---")
    tree_levels = st.session_state.full_node.block.merkle_tree.tree_levels
    
    if not tree_levels:
        return
    
    num_levels = len(tree_levels)
    
    for level_idx in range(num_levels):
        level = tree_levels[level_idx]
        
        if level_idx == 0:
            log_message(f"\nLevel {level_idx} (LEAF NODES - Transactions):")
        elif level_idx == num_levels - 1:
            log_message(f"\nLevel {level_idx} (ROOT NODE):")
        else:
            log_message(f"\nLevel {level_idx} (Intermediate Nodes):")
        
        for idx, node_hash in enumerate(level):
            if level_idx == 0 and idx < len(st.session_state.transactions):
                tx_data = st.session_state.transactions[idx].data
                log_message(f'  [{idx}] {node_hash[:16]}... ("{tx_data}")')
            else:
                log_message(f"  [{idx}] {node_hash[:16]}...")
    
    log_message(f"\n✓ Merkle Root: {st.session_state.full_node.block.merkle_tree.root[:32]}...")

def verify_transaction(tx_index, tamper=False):
    """Verify a specific transaction"""
    if not st.session_state.full_node or not st.session_state.transactions:
        return False, "No block created yet"
    
    log_message("\n==============================================")
    log_message("--- [VERIFICATION PHASE] ---")
    
    tx = st.session_state.transactions[tx_index]
    txid_to_verify = tx.txid
    display_name = f'"{tx.data}"'
    
    # Tampering simulation
    if tamper:
        log_message(f"\n[TEST]: Tampering TXID for '{tx.data}' to simulate fraud\n")
        txid_to_verify = txid_to_verify[:20] + "TAMPERED" + txid_to_verify[28:]
    
    log_message("\n--- [NETWORK SIM: 'Must have 2'] ---")
    log_message(f"SPV Client: I need to verify transaction: {display_name}")
    log_message("SPV Client: Sending request for Merkle Proof to Full Node... 📡")
    
    # Get proof from full node
    proof = st.session_state.full_node.get_merkle_proof(tx.txid)
    
    log_message("Full Node: Proof found. Sending proof back to SPV Client... 📦")
    
    log_message("\n--- [VERIFICATION SIM: 'Must have 1'] ---")
    
    # Verify using SPV client
    result = verify_with_proof(txid_to_verify, proof)
    
    # Update stats
    st.session_state.stats['total_verifications'] += 1
    if result:
        st.session_state.stats['successful_verifications'] += 1
    else:
        st.session_state.stats['failed_verifications'] += 1
    
    return result, display_name

def verify_with_proof(txid, proof):
    """Manual verification with detailed logging"""
    if not st.session_state.spv_client.block_header:
        log_message("SPV Client: Error! No block header to verify against.")
        return False
    
    if proof is None:
        log_message("SPV Client: Error! Invalid proof received (None).")
        return False
    
    log_message(f"SPV Client: Starting verification for TXID: {txid[:10]}...")
    
    calculated_hash = txid
    
    step_num = 1
    for sibling_hash, side in proof:
        log_message(f"   > Step {step_num}: Hashing with {side} sibling: {sibling_hash[:10]}...")
        
        if side == 'right':
            combined_data = calculated_hash + sibling_hash
        else:
            combined_data = sibling_hash + calculated_hash
        
        from backend import double_sha256
        calculated_hash = double_sha256(combined_data)
        log_message(f"   > New calculated hash: {calculated_hash[:10]}...")
        step_num += 1
    
    log_message(f"\nSPV Client: Final Calculated Root: {calculated_hash}")
    
    target_root = st.session_state.spv_client.block_header['merkle_root']
    log_message(f"SPV Client: Expected Header Root:  {target_root}")
    
    if calculated_hash == target_root:
        log_message("   ✅ SUCCESS: Calculated root matches header root!")
        log_message("   ✅ This transaction is verified as part of the block.")
        return True
    else:
        log_message("   ❌ FAILED: Calculated root does NOT match header root.")
        log_message("   ❌ This transaction is INVALID or not in this block.")
        return False

# Main app
st.title("🔗 SPV Transaction Verification Simulator")
st.markdown("**Enhanced Edition** - Demonstrating Simplified Payment Verification in Blockchain")
st.markdown("*Created by Abraham | December 2025*")
st.markdown("---")

# Create tabs
tab1, tab2, tab3 = st.tabs(["📝 Main Simulator", "🌳 Merkle Tree Visualization", "📊 Statistics Dashboard"])

with tab1:
    col1, col2 = st.columns([1, 1])
    
    with col1:
        st.subheader("1. Simulation Setup")
        
        # Transaction input
        default_txs = "Alice pays Bob\nCarol pays David\nEve pays Frank\nGrace pays Heidi"
        tx_input = st.text_area(
            "Enter transactions (one per line):",
            value=default_txs,
            height=150,
            key="tx_input"
        )
        
        # File operations
        col_load, col_save = st.columns(2)
        
        with col_load:
            uploaded_file = st.file_uploader("Load Scenario", type=['json'], key="file_upload")
            if uploaded_file is not None:
                try:
                    scenario = json.load(uploaded_file)
                    st.session_state.tx_input = '\n'.join(scenario.get('transactions', []))
                    st.success(f"✅ Loaded {len(scenario.get('transactions', []))} transactions")
                except Exception as e:
                    st.error(f"❌ Error loading file: {str(e)}")
        
        with col_save:
            if st.download_button(
                label="Save Scenario",
                data=json.dumps({
                    "transactions": tx_input.split('\n'),
                    "timestamp": datetime.now().isoformat()
                }, indent=2),
                file_name=f"scenario_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                mime="application/json"
            ):
                st.success("✅ Scenario downloaded!")
        
        # Create block button
        if st.button("🔨 Create Block & Sync Client", type="primary", use_container_width=True):
            tx_list = tx_input.split('\n')
            if create_block(tx_list):
                st.success("✅ Block created successfully!")
                st.rerun()
    
    with col2:
        st.subheader("2. Run Verification")
        
        if st.session_state.full_node and st.session_state.transactions:
            # Transaction selector
            tx_options = [f'"{tx.data}" (ID: {tx.txid[:10]}...)' 
                         for tx in st.session_state.transactions]
            selected_idx = st.selectbox("Select Transaction to Verify:", 
                                       range(len(tx_options)),
                                       format_func=lambda x: tx_options[x])
            
            # Verification buttons
            col_verify, col_batch = st.columns(2)
            
            with col_verify:
                if st.button("🔍 Run SPV Verification", use_container_width=True):
                    # Check if this is "Eve pays Frank" for tampering demo
                    tamper = "Eve pays Frank" in st.session_state.transactions[selected_idx].data
                    result, name = verify_transaction(selected_idx, tamper=tamper)
                    st.rerun()
            
            with col_batch:
                if st.button("📦 Batch Verify All", use_container_width=True):
                    log_message("\n==============================================")
                    log_message("--- [BATCH VERIFICATION MODE] ---")
                    log_message(f"Verifying {len(st.session_state.transactions)} transactions...\n")
                    
                    batch_results = []
                    for idx, tx in enumerate(st.session_state.transactions, 1):
                        log_message(f"\n[{idx}/{len(st.session_state.transactions)}] Verifying: \"{tx.data}\"")
                        tamper = "Eve pays Frank" in tx.data
                        result, _ = verify_transaction(idx-1, tamper=tamper)
                        batch_results.append(result)
                    
                    success_count = sum(batch_results)
                    log_message("\n==============================================")
                    log_message("--- [BATCH VERIFICATION SUMMARY] ---")
                    log_message(f"Total: {len(batch_results)} | Success: {success_count} | Failed: {len(batch_results) - success_count}")
                    st.rerun()
        else:
            st.info("ℹ️ Please create a block first by clicking 'Create Block & Sync Client'")
    
    # Log area
    st.subheader("Simulation Log (Must have 1 & 2)")
    if st.session_state.log_messages:
        log_text = '\n'.join(st.session_state.log_messages)
        st.text_area("", value=log_text, height=400, key="log_display")
    else:
        st.info("👋 Welcome! Enter transactions on the left and click 'Create Block' to begin.")

with tab2:
    st.subheader("🌳 Merkle Tree Structure")
    
    if st.session_state.full_node:
        tree_levels = st.session_state.full_node.block.merkle_tree.tree_levels
        
        # Display tree structure
        st.markdown("### Visual Representation")
        
        num_levels = len(tree_levels)
        for level_idx in range(num_levels):
            level = tree_levels[level_idx]
            
            if level_idx == 0:
                st.markdown(f"**Level {level_idx}: LEAF NODES (Transactions)** 🔵")
            elif level_idx == num_levels - 1:
                st.markdown(f"**Level {level_idx}: ROOT NODE** 🟢")
            else:
                st.markdown(f"**Level {level_idx}: Intermediate Nodes** 🟡")
            
            # Display nodes in columns
            cols = st.columns(len(level))
            for idx, (col, node_hash) in enumerate(zip(cols, level)):
                with col:
                    if level_idx == 0 and idx < len(st.session_state.transactions):
                        tx_data = st.session_state.transactions[idx].data
                        st.code(f"{node_hash[:12]}...\n({tx_data})", language="")
                    else:
                        st.code(f"{node_hash[:12]}...", language="")
        
        st.success(f"✓ Merkle Root: `{st.session_state.full_node.block.merkle_tree.root[:32]}...`")
        
    else:
        st.info("ℹ️ Create a block in the Main Simulator tab to see the Merkle tree visualization.")

with tab3:
    st.subheader("📊 Verification Statistics Dashboard")
    
    # Display metrics
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Total Verifications", st.session_state.stats['total_verifications'])
    
    with col2:
        st.metric("Successful", st.session_state.stats['successful_verifications'], 
                 delta=None, delta_color="normal")
    
    with col3:
        st.metric("Failed", st.session_state.stats['failed_verifications'],
                 delta=None, delta_color="inverse")
    
    with col4:
        total = st.session_state.stats['total_verifications']
        success_rate = (st.session_state.stats['successful_verifications'] / total * 100) if total > 0 else 0
        st.metric("Success Rate", f"{success_rate:.1f}%")
    
    # Reset button
    if st.button("🔄 Reset Statistics"):
        st.session_state.stats = {
            'total_verifications': 0,
            'successful_verifications': 0,
            'failed_verifications': 0
        }
        st.rerun()
    
    st.markdown("---")
    st.info(f"📅 Session started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

# Sidebar
with st.sidebar:
    st.header("ℹ️ About")
    st.markdown("""
    **SPV Transaction Verification Simulator**
    
    **Created by:** Abraham  
    **Date:** December 2025  
    **Project:** Blockchain SPV Demonstration
    
    This application demonstrates:
    - ✅ **Must Have 1**: SPV Verification Process
    - ✅ **Must Have 2**: Network Communication
    
    **Enhanced Features:**
    - 🎨 Visual Merkle Tree Display
    - 📊 Batch Verification
    - 📈 Statistics Dashboard
    - 💾 Save/Load Scenarios
    """)
    
    st.markdown("---")
    st.markdown("### 🚀 Quick Start")
    st.markdown("""
    1. Enter transactions or load a scenario
    2. Click "Create Block & Sync Client"
    3. Select a transaction and verify
    4. View Merkle tree visualization
    5. Check statistics dashboard
    """)
    
    st.markdown("---")
    st.markdown("### 🔒 Security Demo")
    st.info("💡 Try verifying 'Eve pays Frank' to see tampering detection in action!")
