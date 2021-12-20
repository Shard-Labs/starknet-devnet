import "@shardlabs/starknet-hardhat-plugin";

module.exports = {
    cairo: {
        venv: "active"
    },
    networks: {
        devnet: {
            url: "http://localhost:5000"
        }
    },
    mocha: {
        starknetNetwork: "devnet"
    }
}
