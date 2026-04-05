let cachedWindowId = null;

const getWindowId = async () => {
    if (cachedWindowId !== null) return cachedWindowId;
    cachedWindowId = await window?.windowAPI?.getWindowId?.() ?? '0';
    return cachedWindowId;
};

export const getItem = async (key) => {
    const id = await getWindowId();
    return localStorage.getItem(`${key}_w${id}`);
};

export const setItem = async (key, value) => {
    const id = await getWindowId();
    localStorage.setItem(`${key}_w${id}`, value);
};

export const removeItem = async (key) => {
    const id = await getWindowId();
    localStorage.removeItem(`${key}_w${id}`);
};