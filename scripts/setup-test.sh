# Generate JSON schemas (web/src/schema/*.json) from the TypeScript types in web/src/types.ts.
# They are used to validate data in tests.

TYPES_FILE=web/src/types.ts
OUT_DIR=web/src/schema
OPTS="--no-type-check"

(
  set -x
  npx ts-json-schema-generator --path $TYPES_FILE --type AppData --out $OUT_DIR/app.json $OPTS
  npx ts-json-schema-generator --path $TYPES_FILE --type PreviewData --out $OUT_DIR/preview.json $OPTS
)

echo Completed.
