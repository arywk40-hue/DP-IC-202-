// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

/// Append-only commitments. Input truth and gateway clocks are not verified.
contract IndraAnchor {
    address public immutable owner;
    mapping(bytes32 => bytes32) public roots;
    event Anchored(bytes32 indexed batchId, bytes32 root);
    constructor() { owner = msg.sender; }
    function anchor(bytes32 batchId, bytes32 root) external {
        require(msg.sender == owner, "Unauthorized");
        require(root != bytes32(0), "Empty root");
        require(roots[batchId] == bytes32(0), "Duplicate batch");
        roots[batchId] = root;
        emit Anchored(batchId, root);
    }
}
