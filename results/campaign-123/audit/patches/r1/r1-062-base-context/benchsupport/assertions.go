package benchsupport
import ("testing"; "encoding/json")
func Check(t *testing.T, actual, expected interface{}) {
 a, err := json.Marshal(actual); if err != nil {t.Fatal(err)}
 b, err := json.Marshal(expected); if err != nil {t.Fatal(err)}
 if string(a) != string(b) {t.Fatalf("contract mismatch: %s != %s", a,b)}
}
