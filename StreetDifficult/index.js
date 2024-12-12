/**
 * @type {"agent" | number[]} Either "agent", meaning the interface is in agent mode (can see all listings+prices) or otherwise in client mode (can only see the listings in the array, no pricing information).
 */
let user_mode = "agent";

function die(msg) {
    throw new Error(msg);
}

/**
 * @template A
 * @param {() => A} fn A thunk
 * @returns {() => A} A memoized version of the thunk
 */
function memoize(fn) {
    if (fn.length == 0) {
        let value = undefined;

        return () => {
            if (value === undefined) value = fn();
            if (value === undefined) die(`Thunk ${fn} failed`);
            return value
        }
    } else if (fn.length == 1) {
        let table = {};

        return (o) => {
            if (table[o] === undefined) table[o] = fn(o);
            if (table[o] === undefined) die(`Thunk ${fn} failed on input ${o}`);
            return table[o];
        }
    }
}

/**
 * @param {string} el The ID of the element you want to find 
 * @returns {() => HTMLElement}
 */
function ref_id(el) {
    return () => document.getElementById(el);
}

const searchBar = ref_id("search-bar");
const searchResult = ref_id("search-result");
const resultsList = ref_id("results-list");
const selectedResult = ref_id("selected-result");

/** @type {() => HTMLInputElement} */
const locationInput = ref_id("location");
/** @type {() => HTMLInputElement} */
const rentMin = ref_id("rent-min");
/** @type {() => HTMLInputElement} */
const rentMax = ref_id("rent-max");
/** @type {() => HTMLInputElement} */
const baths = ref_id("baths");
/** @type {() => HTMLInputElement} */
const beds = ref_id("beds");

/**
 * @typedef {{
 *   url: string,
 *   width: number,
 * }} Photo
 *
 * @typedef {{
 *   address: object,
 *   bedrooms: number,
 *   bathrooms: number,
 *   price: number,
 *   zipcode: string,
 *   photos: {mixedSources: {jpeg: Photo[]}}[],
 *   description: string,
 *   schools: object[],
 *   longitude: number,
 *   latitude: number,
 *   zpid: number
 *   property: object[],
 * }} Apartment
 */

/**
 * @param {Apartment} listing
 * @returns {HTMLElement} The listing rendered as a preview
 */

function par(text) {
    let txt = document.createElement("p");
    txt.innerText = text;
    return txt
}

function nodePreview(listing) {
    let node = document.createElement("li");

    let preview = document.createElement("img");
    preview.src = listing.photos[0].mixedSources.jpeg[0].url;

    node.appendChild(preview);
    node.appendChild(par(`${listing.address.streetAddress}, ${listing.zipcode}`));
    node.appendChild(par(details(listing)));

    node.onclick = (_el) => {
        select(listing);
    };

    return node;
}

const DATASET_URL = "./dataset.json";


/** @type {() => Promise<Apartment[]>} */
const dataset = memoize(
    async () => {
        const raw_data = await fetch(DATASET_URL);

        /** @type {Apartment[]} */
        let json_data = await raw_data.json();

        if (user_mode != "agent") {
            json_data = json_data.flatMap((apt) => {
                if (user_mode.indexOf(apt.zpid) == -1) {
                    return [];
                } else {
                    apt.price = NaN;
                    return [apt];
                }
            });
        }

        return json_data;
    });

/**
 * @template A
 * @param {A[]} arr
 * @param {(x: A) => number} key
 * @param {A | undefined} start
 * @returns {A | undefined}
 */
function max_by(arr, key = ((o) => o), start = undefined) {
    return arr.reduce((acc, next) => {
        let score = key(next);
        return score > acc[0] ? [score, next] : acc;
    }, [Number.NEGATIVE_INFINITY, start])[1];
}

const Geocoder = memoize(async () => {
    let { Geocoder } = await google.maps.importLibrary("geocoding");
    return new Geocoder();
});

const geocode = memoize(async (address) => {
    return await (await Geocoder()).geocode({
        address: address,
        componentRestrictions: { locality: "New York City", country: "US" }
    }).catch(die);
});

function loc(obj) {
    const val = (obj) => typeof obj == "function" ? obj() : obj;

    if (typeof obj !== "object") return undefined;
    const lat = val(obj['lat'] || obj['latitude'])
    const lng = val(obj['lng'] || obj['longitude'])
    return lat && lng && { lat: lat, lng: lng };
}

function near(v1, v2, epsilon = 0.0001) {
    if (typeof (v1) == "object" && typeof (v2) == "object") {
        const def = { lat: undefined, lng: undefined }
        const { lat: lat1, lng: lng1 } = loc(v1) || def;
        const { lat: lat2, lng2: lng2 } = loc(v2) || def;
        return near(lat1, lat2, epsilon) && near(lng1, lng2, epsilon);
    } else if (typeof (v1) == "number" && typeof (v2) == "number") {
        return Math.abs(v1 - v2) < epsilon;
    } else {
        return false;
    }
}

async function run_search() {
    const loc = locationInput();
    let ds = await dataset();
    const gc = (await geocode(loc.value)).results;

    let dsp = ds.filter((a) => {
        if (loc.value.trim() !== "") {
            const al = { lat: a.latitude, lng: a.longitude };

            const right_area = gc.find((r) => {
                if (r.geometry.location_type == "APPROXIMATE") {
                    return r.geometry.bounds.contains(al);
                } else {
                    return near(r.geometry.location, a);
                }
            });

            if (!right_area) return false;
        }

        // Small hack: valueAsNumber is NaN for empty/invalid inputs,
        // which will never pass a comparison check, so we don't have
        // to check that case explicitly.
        if (rentMin().valueAsNumber > a.price) return false;
        if (rentMax().valueAsNumber < a.price) return false;
        if (beds().valueAsNumber > a.bedrooms) return false;
        if (baths().valueAsNumber > a.bathrooms) return false;

        return true;
    });

    console.log(`Filtered out ${ds.length - dsp.length} listings`);

    updateListings(dsp);
}

/**
 * @param {Apartment} listing
 */
function details(listing) {
    const suffix = isNaN(listing.price) ? "" : ` - $${listing.price}`;
    return `${listing.bedrooms} bed/${listing.bathrooms} bath${suffix}`;
}

/**
 * @param {Apartment} listing
 */
async function select(listing) {
    await google.maps.importLibrary("marker");

    let node = document.createElement("div");
    node.id = "selected-result";

    node.innerHTML = `
<h1>${listing.address.streetAddress}, ${listing.zipcode}</h1>
<h2>Listing ID: ${listing.zpid}</h2>
<h2>${details(listing)}</h2>
<p>${listing.description}</p>
`;

    let gallery = document.createElement("div");

    for (let o of listing.photos) {
        let ph = o.mixedSources.jpeg;
        let image = document.createElement("img");
        image.src = max_by(ph, (k) => k.width).url;
        gallery.appendChild(image)
    }

    node.appendChild(gallery);

    let posn = `${listing.latitude}, ${listing.longitude}`;

    let marker = document.createElement("gmp-advanced-marker");
    marker.setAttribute("position", posn);
    marker.title = "Listing";

    let map = document.createElement("gmp-map");
    map.setAttribute("center", posn);
    map.setAttribute("zoom", 16);
    map.setAttribute("map-id", "DEMO_MAP_ID");
    map.title = "Listing Area"

    map.appendChild(marker);

    node.appendChild(map);

    for (let {title, values} of listing.property) {
        let nd = document.createElement("h2");
        nd.innerText = title;
        node.appendChild(nd);

        let list = document.createElement("ul");

        for (let value of values) {
            let li = document.createElement("li");
            li.innerText = value;
            list.appendChild(li);
        }

        node.appendChild(list);
    }

    let schools = document.createElement("h2");
    schools.innerText = "Nearby Schools";
    node.appendChild(schools);
    
    let schoolList = document.createElement("ul");

    for (let {distance, link, level, name, rating, type} of listing.schools) {
        let li = document.createElement("li");
        li.innerHTML = `<a href="${link}" target="_blank" rel="noopener noreferrer">${name}</a> (a ${type.toLowerCase()} ${level.toLowerCase()} school, rated ${rating}/10) is ${distance} miles away`;

        schoolList.appendChild(li);
    }

    node.appendChild(schoolList);


    selectedResult().replaceWith(node);

    tns({ container: gallery, mode: "gallery", nav: false, edgePadding: 20 });
}

/**
 * @param {Apartment[]} listings
 */
function updateListings(listings) {
    selectedResult().innerHTML = "<h2>Select a listing from the list on the left.</h2>";

    if (user_mode === "agent")
        listings.sort((a, b) => a.price - b.price);
    else
        listings.sort((a, b) => user_mode.indexOf(a.zpid) - user_mode.indexOf(b.zpid));

    resultsList().replaceChildren(...listings.map(nodePreview));
}

addEventListener("load", async (_win, _ev) => {
    while (true) {
        const response = prompt("If you are a client, enter your apartment listings (a series of comma-separated numbers). Otherwise, press enter");
        console.log(response);

        if (response === "") {
            user_mode = "agent";
            break;
        } else if (response === null) {
            continue;
        } else {
            let list = response.split(",").map((o) => Number.parseInt(o.trim()));
            if (list.indexOf(NaN) === -1) {
                user_mode = list;
                break;
            }
        }
    }
    let ds = await dataset().catch(die);
    updateListings(ds);
});
