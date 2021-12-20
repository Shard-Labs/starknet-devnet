import "@shardlabs/starknet-hardhat-plugin";

module.exports = {
    cairo: {
        version: "latest"
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
