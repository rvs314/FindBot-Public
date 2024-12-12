website: StreetDifficult/dataset.json
	echo "Website Built"

StreetDifficult/dataset.json: BrightData/zillow-sample.json
	python3 BrightData/process.py $< $@

client:
	cd ./lk-FindBot-agent; ./venv/bin/python3 findbot.py

.PHONY: website update client
