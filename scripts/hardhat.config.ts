import "@shardlabs/starknet-hardhat-plugin";

// You need to export an object to set up your config
// Go to https://hardhat.org/config/ to learn more

/**
 * @type import('hardhat/config').HardhatUserConfig
 */
module.exports = {
  solidity: "0.8.4",
  cairo: {
    version: "0.4.2"
  },
  networks: {
    starknetLocalhost: {
      url: "http://localhost:5000"
    }
  },
  mocha: {
    starknetNetwork: "starknetLocalhost"
  }
};
