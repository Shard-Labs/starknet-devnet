import "@shardlabs/starknet-hardhat-plugin";

module.exports = {
    starknet: {
        venv: "active",
        network: "devnet",
        wallets: {
          OpenZeppelin: {
            accountName: "OpenZeppelin",
            modulePath: "starkware.starknet.wallets.open_zeppelin.OpenZeppelinAccount",
            accountPath: "~/.starknet_accounts"
          }
        }
    },
    networks: {
        devnet: {
            url: "http://localhost:5000"
        }
    }
}