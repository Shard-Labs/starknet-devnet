const L1L2Example = artifacts.require("L1L2Example");
const MockStarknetMessaging = artifacts.require("MockStarknetMessaging");
module.exports = function(deployer) {
    deployer.deploy(MockStarknetMessaging).then(function() {
        return deployer.deploy(L1L2Example, MockStarknetMessaging.address);
      });
};
