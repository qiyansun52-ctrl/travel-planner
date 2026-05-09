.PHONY: gen-types check-types

gen-types:
	cd web && npm run gen:types

check-types:
	cd web && npm run check:types
