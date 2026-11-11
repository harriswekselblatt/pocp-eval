package gjson

// Differential probe for constructed-02 gjson cases; copied into a checkout only for the oracle.

import (
	"encoding/json"
	"fmt"
	"testing"
)

func TestZZProbe(t *testing.T) {
	words := []string{"", "a", "A", "b", "B", "z", "Z", "@", "[", "`", "_", "{", "ab", "aB", "Ab", "AB", "abc", "ABD", "a[", "A[", "a`", "A`", "Zz", "zZ", "é", "É", "hello", "HELLO", "Hello World", "hello world!"}
	var less []bool
	for _, x := range words {
		for _, y := range words {
			less = append(less, stringLessInsensitive(x, y))
			less = append(less, Result{Type: String, Str: x}.Less(Result{Type: String, Str: y}, false))
		}
	}
	boolStrs := []string{"", "true", "TRUE", "True", "tRuE", "false", "FALSE", "1", "0", "t", "f", "T", "F", "yes", "no", " true", "2"}
	var bools [][3]bool
	for _, s := range boolStrs {
		r := Result{Type: String, Str: s}
		bools = append(bools, [3]bool{r.Bool(), trueish(r), falseish(r)})
	}
	for _, r := range []Result{{Type: Null}, {Type: True}, {Type: False}, {Type: Number, Num: 0}, {Type: Number, Num: 2}, {Type: JSON, Raw: "{}"}} {
		bools = append(bools, [3]bool{r.Bool(), trueish(r), falseish(r)})
	}
	doc := `{"vals":[{"a":1,"b":true},{"a":2,"b":"TRUE"},{"a":3,"b":"0"},{"a":4,"b":0},{"a":5,"b":"x"},{"a":6}],"names":["bob","Alice","alice","Bob","carol"]}`
	queries := []string{"vals.#(b==~true)#.a", "vals.#(b==~false)#.a", "names|@sort", "names.#(%\"a*\")#", "vals.#.b"}
	var qs []string
	for _, q := range queries {
		qs = append(qs, Get(doc, q).Raw)
	}
	out, _ := json.Marshal(map[string]any{"less": less, "bools": bools, "queries": qs})
	fmt.Println("PROBE=" + string(out))
}
