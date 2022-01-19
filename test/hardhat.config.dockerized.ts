import "@shardlabs/starknet-hardhat-plugin";

if (!process.env.CAIRO_LANG_VERSION) {
    console.log("CAIRO_LANG_VERSION is undefined.")
    process.exit(1);
}

module.exports = {
    cairo: {
        version: process.env.CAIRO_LANG_VERSION
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
