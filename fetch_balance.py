from solana.rpc.api    import Client
from solders.pubkey    import Pubkey as PublicKey

client      = Client("https://api.devnet.solana.com")
YOUR_ADDRESS = "E16t8Ri3AjSGwWEmZNRo9KsQpwb8PvbpEphhRZRKYPK1"

# fetch the balance response object…
resp     = client.get_balance(PublicKey.from_string(YOUR_ADDRESS))

# …and read lamports from its .value
lamports = resp.value

# convert to SOL
sol      = lamports / 1e9

print(f"Your SOL balance is: {sol:.4f} SOL")
