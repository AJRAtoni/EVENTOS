import crypto from 'node:crypto';
import fs from 'node:fs/promises';

const AIRTABLE_BASE_ID = 'apphXPfmF1OwvCPWC';
const AIRTABLE_TABLE_NAME = 'eventos';
const AIRTABLE_SORT_FIELD = 'FechaOrden';
const OUTPUT_PATH = 'data/events.json';
const PLACEHOLDER_IMAGE = 'images/logo.webp';

const {
    AIRTABLE_TOKEN,
    CLOUDINARY_URL
} = process.env;

const parseCloudinaryUrl = (url) => {
    if (!url) return {};

    try {
        const parsed = new URL(url);

        return {
            CLOUDINARY_CLOUD_NAME: parsed.hostname,
            CLOUDINARY_API_KEY: decodeURIComponent(parsed.username),
            CLOUDINARY_API_SECRET: decodeURIComponent(parsed.password)
        };
    } catch (error) {
        throw new Error('CLOUDINARY_URL must use cloudinary://<api_key>:<api_secret>@<cloud_name>');
    }
};

const cloudinaryUrlConfig = parseCloudinaryUrl(CLOUDINARY_URL);
const cloudinaryConfig = {
    CLOUDINARY_CLOUD_NAME: process.env.CLOUDINARY_CLOUD_NAME || cloudinaryUrlConfig.CLOUDINARY_CLOUD_NAME,
    CLOUDINARY_API_KEY: process.env.CLOUDINARY_API_KEY || cloudinaryUrlConfig.CLOUDINARY_API_KEY,
    CLOUDINARY_API_SECRET: process.env.CLOUDINARY_API_SECRET || cloudinaryUrlConfig.CLOUDINARY_API_SECRET
};

const {
    CLOUDINARY_CLOUD_NAME,
    CLOUDINARY_API_KEY,
    CLOUDINARY_API_SECRET
} = cloudinaryConfig;

const uploadImages = Boolean(CLOUDINARY_CLOUD_NAME && CLOUDINARY_API_KEY && CLOUDINARY_API_SECRET);

const requiredEnv = ['AIRTABLE_TOKEN'];
const missingEnv = requiredEnv.filter((name) => !process.env[name]);

if (missingEnv.length > 0) {
    console.error(`Missing required env var(s): ${missingEnv.join(', ')}`);
    process.exit(1);
}

if (!uploadImages) {
    console.warn('Cloudinary env vars not found. Exporting events with placeholder images.');
}

const clean = (value = '') => String(value || '').replace(/\s+/g, ' ').trim();

const stripAccents = (value = '') => clean(value)
    .normalize('NFD')
    .replace(/[\u0300-\u036f]/g, '');

const slugify = (value = '') => stripAccents(value)
    .toLowerCase()
    .replace(/&/g, ' y ')
    .replace(/[^a-z0-9]+/g, '-')
    .replace(/^-|-$/g, '');

const categoryMap = {
    cineytv: 'cineytv',
    deportes: 'deportes',
    festividades: 'festividades',
    tecnologia: 'tecnologia',
    videojuegos: 'videojuegos',
    curiosidades: 'curiosidades'
};

const normalizeCategory = (value) => categoryMap[slugify(value)] || 'curiosidades';

const usedIds = new Map();

const makeId = (date, title) => {
    const base = `evt-${date}-${slugify(title) || 'sin-titulo'}`;
    const seen = usedIds.get(base) || 0;
    usedIds.set(base, seen + 1);
    return seen === 0 ? base : `${base}-${seen + 1}`;
};

const signCloudinaryParams = (params) => {
    const signaturePayload = Object.entries(params)
        .filter(([key, value]) => value !== undefined && value !== null && value !== '' && !['file', 'api_key', 'resource_type', 'cloud_name'].includes(key))
        .sort(([a], [b]) => a.localeCompare(b))
        .map(([key, value]) => `${key}=${value}`)
        .join('&');

    return crypto
        .createHash('sha1')
        .update(`${signaturePayload}${CLOUDINARY_API_SECRET}`)
        .digest('hex');
};

const fetchJson = async (url, options = {}) => {
    const response = await fetch(url, options);

    if (!response.ok) {
        const body = await response.text();
        throw new Error(`${response.status} ${response.statusText}: ${body}`);
    }

    return response.json();
};

const fetchAirtableRecords = async () => {
    const records = [];
    let offset = '';

    do {
        const url = new URL(`https://api.airtable.com/v0/${AIRTABLE_BASE_ID}/${encodeURIComponent(AIRTABLE_TABLE_NAME)}`);
        url.searchParams.set('pageSize', '100');
        url.searchParams.set('sort[0][field]', AIRTABLE_SORT_FIELD);
        url.searchParams.set('sort[0][direction]', 'asc');
        if (offset) url.searchParams.set('offset', offset);

        const data = await fetchJson(url, {
            headers: {
                Authorization: `Bearer ${AIRTABLE_TOKEN}`
            }
        });

        records.push(...(data.records || []));
        offset = data.offset || '';
    } while (offset);

    return records;
};

const uploadToCloudinary = async ({ eventId, attachment }) => {
    if (!uploadImages || !attachment?.url) return PLACEHOLDER_IMAGE;

    const timestamp = Math.floor(Date.now() / 1000);
    const publicId = `eventos/${eventId}`;
    const params = {
        timestamp,
        public_id: publicId,
        overwrite: 'true',
        invalidate: 'true'
    };
    const signature = signCloudinaryParams(params);
    const form = new FormData();

    form.set('file', attachment.url);
    form.set('api_key', CLOUDINARY_API_KEY);
    form.set('timestamp', String(timestamp));
    form.set('public_id', publicId);
    form.set('overwrite', 'true');
    form.set('invalidate', 'true');
    form.set('signature', signature);

    const data = await fetchJson(`https://api.cloudinary.com/v1_1/${CLOUDINARY_CLOUD_NAME}/image/upload`, {
        method: 'POST',
        body: form
    });

    return data.secure_url || PLACEHOLDER_IMAGE;
};

const mapRecordToEvent = async (record) => {
    const fields = record.fields || {};
    const date = clean(fields.FechaOrden || '');
    const title = clean(fields.Titulo || 'Sin Titulo');

    if (!date) return null;

    const id = makeId(date, title);
    const brand = slugify(fields.Franquicia || '');
    const sites = ['eventos'];
    const firstImage = Array.isArray(fields.Imagen) ? fields.Imagen[0] : null;

    if (brand === 'marvel') sites.push('marvel');
    if (brand === 'dc') sites.push('dc');

    const tags = [fields.Tipo, fields.Franquicia, fields.CategoriaEvento]
        .map(slugify)
        .filter(Boolean);

    return {
        id,
        title,
        description: '',
        date,
        category: normalizeCategory(fields.CategoriaEvento || ''),
        image: await uploadToCloudinary({ eventId: id, attachment: firstImage }),
        url: clean(fields.IMDbURL || fields.URL || ''),
        status: 'published',
        sites,
        brands: brand ? [brand] : [],
        tags: [...new Set(tags)]
    };
};

const records = await fetchAirtableRecords();
const events = [];

for (const record of records) {
    const event = await mapRecordToEvent(record);
    if (event) events.push(event);
}

events.sort((a, b) => a.date.localeCompare(b.date) || a.title.localeCompare(b.title, 'es'));

const output = {
    version: 1,
    updatedAt: new Date().toISOString(),
    source: uploadImages ? 'airtable-export-cloudinary-images' : 'airtable-export',
    events
};

await fs.writeFile(OUTPUT_PATH, `${JSON.stringify(output, null, 2)}\n`);

const withCloudinaryImages = events.filter((event) => event.image.includes('res.cloudinary.com')).length;
console.log(`Exported ${events.length} events to ${OUTPUT_PATH}.`);
console.log(`Cloudinary images: ${withCloudinaryImages}/${events.length}.`);
