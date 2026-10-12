// Demo: simulated payments. Fictional roster; synthetic INR fees in integer paise.
export const ARTISTS = Object.freeze([
  { id: "a1", name: "Riya Saranga (fictional)", genre: "Bollywood", city: "Mumbai", packages: [{ id: "p1", label: "Basic (1 hour)", feePaise: 2500000 }, { id: "p2", label: "Standard (2 hours)", feePaise: 4500000 }, { id: "p3", label: "Premium (full event)", feePaise: 7500000 }], slots: ["10:00", "14:00", "18:00", "20:00"] },
  { id: "a2", name: "The Tabla Tides (fictional)", genre: "Fusion", city: "Pune", packages: [{ id: "p1", label: "Acoustic", feePaise: 3000000 }], slots: ["10:00", "14:00", "18:00", "20:00"] },
  { id: "a3", name: "DJ Neel Akash (fictional)", genre: "Electronic", city: "Bengaluru", packages: [{ id: "p1", label: "Club night", feePaise: 4000000 }, { id: "p2", label: "Wedding", feePaise: 7500000 }], slots: ["10:00", "14:00", "18:00", "20:00"] },
  { id: "a4", name: "Meera Raag Ensemble (fictional)", genre: "Classical", city: "Delhi", packages: [{ id: "p1", label: "Recital", feePaise: 3500000 }], slots: ["10:00", "14:00", "18:00", "20:00"] }
]);
