package main

import (
	"errors"
	"log"
	"os"
	"time"

	"github.com/pocketbase/pocketbase"
	"github.com/pocketbase/pocketbase/core"
)

func newFeedApp(dataDir string) *pocketbase.PocketBase {
	app := pocketbase.NewWithConfig(pocketbase.Config{DefaultDataDir: dataDir})
	started := time.Now()
	app.OnBootstrap().BindFunc(func(e *core.BootstrapEvent) error {
		if err := e.Next(); err != nil {
			return err
		}
		return app.RunAppMigrations()
	})
	app.OnServe().BindFunc(func(e *core.ServeEvent) error {
		key := []byte(os.Getenv("JWT_SECRET"))
		if len(key) == 0 {
			return errors.New("JWT_SECRET is required")
		}
		registerFeedRoutes(e, key, started)
		return e.Next()
	})
	return app
}

func main() {
	app := newFeedApp("/data")
	if err := app.Start(); err != nil {
		log.Fatal(err)
	}
}
