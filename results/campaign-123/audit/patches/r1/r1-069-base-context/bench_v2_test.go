package gjson
import ("testing"; "os"; "encoding/json"; "fmt"; "github.com/tidwall/gjson/benchsupport")
func TestBenchV2(t *testing.T) {
 b,err := os.ReadFile("testdata/bench-expected.json"); if err != nil {t.Fatal(err)}
 var expected interface{}; if err=json.Unmarshal(b,&expected); err != nil {t.Fatal(err)}
 actual := []float64{Get(`{"n":2.5}`, "n").Float(), Get(`{"n":1.25}`, "n").Float()}
 normalized,err:=json.Marshal(actual); if err!=nil {t.Fatal(err)}
 fmt.Println("BENCH_ACTUAL="+string(normalized))
 benchsupport.Check(t,actual,expected)
}
