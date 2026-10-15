package main

import (
	"testing"

	"github.com/pocketbase/dbx"
)

func TestNativeDefaultConnectionPragmas(t *testing.T) {
	app := nativeTestApp(t)
	var engineVersion, engineSource string
	if err := app.DB().NewQuery("SELECT sqlite_version(),sqlite_source_id()").Row(&engineVersion, &engineSource); err != nil {
		t.Fatal(err)
	}
	if engineVersion != "3.53.4" || engineSource != "2026-07-24 19:02:57 bf7c7f30031888f4e796e429ab3978879485813aaca6f641c7b33e4e09459bcc" {
		t.Fatalf("native bundled SQLite version/source differs: %s %s", engineVersion, engineSource)
	}
	t.Logf("native SQLite engine=%s source=%s", engineVersion, engineSource)
	for name, connection := range map[string]dbx.Builder{
		"concurrent": app.ConcurrentDB(), "nonconcurrent": app.NonconcurrentDB(),
	} {
		for pragma, expected := range map[string]string{
			"journal_mode": "wal", "synchronous": "1", "foreign_keys": "1",
			"busy_timeout": "10000", "temp_store": "2", "cache_size": "-32000",
		} {
			var actual string
			if err := connection.NewQuery("PRAGMA " + pragma).Row(&actual); err != nil {
				t.Fatal(err)
			}
			if actual != expected {
				t.Fatalf("native %s %s=%s, expected %s", name, pragma, actual, expected)
			}
			t.Logf("native %s %s=%s", name, pragma, actual)
		}
	}
}
