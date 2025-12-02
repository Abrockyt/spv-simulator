import hashlib

def double_sha256(data):
    """
    A helper function to perform a double SHA-256 hash, 
    which is standard in Bitcoin.
    """
    if not isinstance(data, bytes):
        data = data.encode('utf-8')
    hash1 = hashlib.sha256(data).digest()
    hash2 = hashlib.sha256(hash1).hexdigest()
    return hash2

class Transaction:
    """
    Represents a simple transaction. 
    Its ID is just the double-hash of its data string.
    """
    def __init__(self, data_str):
        self.data = data_str
        self.txid = double_sha256(self.data)

class MerkleTree:
    """
    A class to build a Merkle Tree from a list of transactions 
    and generate proofs.
    """
    def __init__(self, transactions):
        self.transactions = transactions
        self.txids = [tx.txid for tx in self.transactions]
        
        # Build the tree and store all levels for generating proofs
        self.tree_levels = self._build_tree_levels(self.txids)
        
        # The root is the single hash at the top level
        if self.tree_levels:
            self.root = self.tree_levels[-1][0]
        else:
            self.root = None

    def _build_tree_levels(self, leaves):
        """Internal helper to build the tree and store all intermediate levels."""
        if not leaves:
            return []

        levels = [leaves]
        current_level = leaves
        
        while len(current_level) > 1:
            # Handle an odd number of nodes by duplicating the last one
            if len(current_level) % 2 != 0:
                current_level.append(current_level[-1])
            
            next_level = []
            # Pair up and hash nodes to create the next level
            for i in range(0, len(current_level), 2):
                left_child = current_level[i]
                right_child = current_level[i+1]
                parent_hash = double_sha256(left_child + right_child)
                next_level.append(parent_hash)
            
            levels.append(next_level)
            current_level = next_level
            
        return levels

    def get_proof(self, target_txid):
        """
        Generates a Merkle proof for a given transaction ID.
        The proof is a list of tuples: (sibling_hash, 'left'/'right')
        """
        try:
            # Find the starting index of our transaction
            current_index = self.txids.index(target_txid)
        except ValueError:
            return None # Transaction not in tree

        proof = []
        
        # Iterate up the tree from the leaves to the root
        for level in range(len(self.tree_levels) - 1):
            current_level_list = self.tree_levels[level]
            
            # Check for and handle the odd-node-duplicated case
            is_odd_node = (len(current_level_list) % 2 != 0)
            if is_odd_node and current_index == len(current_level_list) - 1:
                # This node was duplicated. Its sibling is itself.
                # We don't add it to the proof, just move to the parent.
                pass
            
            # Determine if the node is a left or right child
            elif current_index % 2 == 0:
                # This is a left child, its sibling is on the right
                sibling_index = current_index + 1
                side = 'right' # The sibling is on the right
                proof.append((current_level_list[sibling_index], side))
            
            else:
                # This is a right child, its sibling is on the left
                sibling_index = current_index - 1
                side = 'left' # The sibling is on the left
                proof.append((current_level_list[sibling_index], side))

            # Move up to the parent node for the next iteration
            current_index = current_index // 2
            
        return proof

class Block:
    """Represents a simplified block, containing transactions and a Merkle tree."""
    def __init__(self, transactions):
        self.transactions = transactions
        self.merkle_tree = MerkleTree(self.transactions)
        
        # The Block Header only contains the Merkle Root for this simulation
        self.header = {
            "merkle_root": self.merkle_tree.root
        }

class FullNode:
    """
    Simulates a "Full Node" that has the entire block and 
    can provide proofs.
    """
    def __init__(self, block):
        self.block = block

    def get_merkle_proof(self, txid):
        """
        Handles a request from a light client for a Merkle proof.
        (This is part of the "Must have 2" simulation).
        """
        print(f"[FullNode] Received request for proof for TXID: {txid[:10]}...")
        proof = self.block.merkle_tree.get_proof(txid)
        if proof:
            print(f"[FullNode] Proof found. Sending {len(proof)} hashes.")
        else:
            print(f"[FullNode] TXID not found in my block.")
        return proof

class SPVClient:
    """
    Simulates a "Lightweight (SPV) Client" that only has the header
    and must verify transactions using proofs.
    """
    def __init__(self):
        self.block_header = None
        # This 'log_callback' is key for connecting to the GUI
        self.log_callback = print 

    def set_header(self, header):
        """Simulates downloading and storing just the block header."""
        self.block_header = header
        self.log("SPV Client: Downloaded and stored block header.")
        self.log(f"   > Header Merkle Root: {self.block_header['merkle_root']}")

    def log(self, message):
        """A wrapper to send log messages to the GUI or console."""
        self.log_callback(message)

    def verify_transaction(self, txid, proof):
        """
        This is the core of "Must have 1".
        It uses the proof to recalculate the Merkle Root.
        Returns True if verification succeeds, False otherwise.
        """
        if not self.block_header:
            self.log("SPV Client: Error! No block header to verify against.")
            return False
            
        if proof is None:
            self.log("SPV Client: Error! Invalid proof received (None).")
            return False

        self.log(f"SPV Client: Starting verification for TXID: {txid[:10]}...")
        
        # Start with the hash of the transaction we want to prove
        calculated_hash = txid
        
        # Iterate through the proof, hashing at each step
        step_num = 1
        for sibling_hash, side in proof:
            self.log(f"   > Step {step_num}: Hashing with {side} sibling: {sibling_hash[:10]}...")
            
            if side == 'right':
                # Our hash is on the left
                combined_data = calculated_hash + sibling_hash
            else:
                # Our hash is on the right
                combined_data = sibling_hash + calculated_hash
                
            # Hash the combined pair to get the parent hash
            calculated_hash = double_sha256(combined_data)
            self.log(f"   > New calculated hash: {calculated_hash[:10]}...")
            step_num += 1
        
        # After the loop, calculated_hash should be the Merkle Root
        self.log(f"\nSPV Client: Final Calculated Root: {calculated_hash}")
        
        target_root = self.block_header['merkle_root']
        self.log(f"SPV Client: Expected Header Root:  {target_root}")
        
        # The final check!
        if calculated_hash == target_root:
            self.log("   ✅ SUCCESS: Calculated root matches header root!")
            self.log("   ✅ This transaction is verified as part of the block.")
            return True
        else:
            self.log("   ❌ FAILED: Calculated root does NOT match header root.")
            self.log("   ❌ This transaction is INVALID or not in this block.")
            return False