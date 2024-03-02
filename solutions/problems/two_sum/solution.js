/**
 * @param {number[]} nums
 * @param {number} target
 * @return {number[]}
 */
var twoSum = function(nums, target) {
    const numObject = {};
    for (let i = 0; i < nums.length; i++) {
        const currentNum = nums[i];
        const complement = target - currentNum;
        if (numObject.hasOwnProperty(complement)) {
        return [numObject[complement], i];
        }
        numObject[currentNum] = i;
    }

};