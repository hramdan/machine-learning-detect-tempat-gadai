/**
 * Pegadaian Spatial API Client Service
 */

const API_BASE_URL = import.meta.env.VITE_API_URL || '';

/**
 * Fetch all pawnshop records across Jabodetabek, optionally filtered by region (wilayah) and/or category (kategori).
 * @param {string} [wilayah] - Region filter (e.g., "Jakarta Selatan", "Depok", "all")
 * @param {string} [kategori] - Category filter (e.g., "BUMN", "Gadai Swasta Berizin", "Gadai Mandiri", "all")
 * @returns {Promise<Array>} List of pawnshop objects
 */
export async function fetchCabang(wilayah = '', kategori = '') {
	try {
		const params = new URLSearchParams();
		if (wilayah && wilayah !== 'All' && wilayah !== 'all') {
			params.append('wilayah', wilayah);
		}
		if (kategori && kategori !== 'All' && kategori !== 'all') {
			params.append('kategori', kategori);
		}

		let url = `${API_BASE_URL}/api/pegadaian`;
		const queryString = params.toString();
		if (queryString) {
			url += `?${queryString}`;
		}

		const response = await fetch(url, {
			method: 'GET',
			headers: { 'Content-Type': 'application/json' }
		});
		if (!response.ok) {
			throw new Error(`HTTP Error ${response.status}: ${response.statusText}`);
		}
		return await response.json();
	} catch (error) {
		console.error('Error in fetchCabang:', error);
		throw error;
	}
}

/**
 * Trigger the automated scraping, geocoding, and spatial 1km proximity analysis pipeline.
 * @returns {Promise<Object>} Scraping pipeline results with total pawnshop count
 */
export async function triggerScraping() {
	try {
		const response = await fetch(`${API_BASE_URL}/api/trigger-scraping`, {
			method: 'POST',
			headers: { 'Content-Type': 'application/json' }
		});
		if (!response.ok) {
			const errorData = await response.json().catch(() => ({}));
			throw new Error(errorData.detail || `Server error: ${response.status}`);
		}
		return await response.json();
	} catch (error) {
		console.error('Error in triggerScraping:', error);
		throw error;
	}
}

/**
 * Trigger spatial 1km density analysis manually.
 * @returns {Promise<Object>} Density distribution and statistics
 */
export async function triggerClustering() {
	try {
		const response = await fetch(`${API_BASE_URL}/api/trigger-clustering`, {
			method: 'POST',
			headers: { 'Content-Type': 'application/json' }
		});
		if (!response.ok) {
			throw new Error(`Clustering failed: ${response.statusText}`);
		}
		return await response.json();
	} catch (error) {
		console.error('Error in triggerClustering:', error);
		throw error;
	}
}

/**
 * Fetch spatial statistics & analytics KPIs (including kategori and density distribution).
 * @returns {Promise<Object>} Distribution metrics across density tiers, categories, and regions
 */
export async function fetchStats() {
	try {
		const response = await fetch(`${API_BASE_URL}/api/stats`, {
			method: 'GET',
			headers: { 'Content-Type': 'application/json' }
		});
		if (!response.ok) {
			throw new Error(`Stats fetch failed: ${response.statusText}`);
		}
		return await response.json();
	} catch (error) {
		console.error('Error in fetchStats:', error);
		throw error;
	}
}
