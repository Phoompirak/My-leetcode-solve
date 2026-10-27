class Solution {
public:
    int romanToInt(string s) {
        unordered_map<char, int> roman;
        roman['I'] = 1;
        roman['V'] = 5;
        roman['X'] = 10;
        roman['L'] = 50;
        roman['C'] =  100;
        roman['D'] =  500;
        roman['M'] = 1000;

        int res = 0;
        for (int i = 0; i < s.size(); i++) {
            if (roman[s[i]]  < roman[s[i + 1]]) {
                res -= roman[s[i]];
            }
            else {
                res += roman[s[i]];
            }
        }

        return res ;
    }
};