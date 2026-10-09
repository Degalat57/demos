/* Synthetic seed data for the demo. Obviously fictional names/numbers. */
(function () {
  function iso(dayOffset, h, m) {
    var d = new Date();
    d.setDate(d.getDate() + dayOffset);
    d.setHours(h, m, 0, 0);
    return d.toISOString();
  }
  function dateOnly(dayOffset) { return iso(dayOffset, 9, 0).slice(0, 10); }

  var techs = ["Mike", "Luis", "Ana", "Sam"];

  var customers = [
    { id: "c1", name: "Jamie Faker", phone: "(555) 210-0101" },
    { id: "c2", name: "Robin Sample", phone: "(555) 210-0102" },
    { id: "c3", name: "Casey Placeholder", phone: "(555) 210-0103" },
    { id: "c4", name: "Avery Dummy", phone: "(555) 210-0104" },
    { id: "c5", name: "Morgan Testman", phone: "(555) 210-0105" },
    { id: "c6", name: "Devon Mock", phone: "(555) 210-0106" },
    { id: "c7", name: "Quinn Example", phone: "(555) 210-0107" },
    { id: "c8", name: "Parker Notreal", phone: "(555) 210-0108" }
  ];

  var vehicles = [
    { id: "v1", customerId: "c1", year: 2018, make: "Toyota", model: "Camry", plate: "DEMO-101", mileage: 84210 },
    { id: "v2", customerId: "c2", year: 2016, make: "Ford", model: "F-150", plate: "DEMO-102", mileage: 121450 },
    { id: "v3", customerId: "c3", year: 2020, make: "Honda", model: "Civic", plate: "DEMO-103", mileage: 39870 },
    { id: "v4", customerId: "c4", year: 2014, make: "Nissan", model: "Altima", plate: "DEMO-104", mileage: 143900 },
    { id: "v5", customerId: "c5", year: 2019, make: "Subaru", model: "Outback", plate: "DEMO-105", mileage: 67530 },
    { id: "v6", customerId: "c6", year: 2012, make: "Chevrolet", model: "Silverado", plate: "DEMO-106", mileage: 168300 },
    { id: "v7", customerId: "c7", year: 2021, make: "Hyundai", model: "Tucson", plate: "DEMO-107", mileage: 28450 },
    { id: "v8", customerId: "c8", year: 2017, make: "Volkswagen", model: "Jetta", plate: "DEMO-108", mileage: 96120 }
  ];

  function tl(arr) { return arr.map(function (t) { return { status: t[0], at: t[1], by: t[2] }; }); }

  var jobs = [
    // Today - waiting (3)
    { id: "j1", vehicleId: "v1", customerId: "c1", complaint: "Vibration at highway speed", scheduledAt: iso(0, 8, 15), status: "waiting", tech: null, timeline: tl([["waiting", iso(0, 8, 15), null]]), inspectionId: null },
    { id: "j2", vehicleId: "v3", customerId: "c3", complaint: "Oil change + rotate tires", scheduledAt: iso(0, 10, 0), status: "waiting", tech: null, timeline: tl([["waiting", iso(0, 10, 0), null]]), inspectionId: null },
    { id: "j3", vehicleId: "v7", customerId: "c7", complaint: "TPMS light on", scheduledAt: iso(0, 13, 15), status: "waiting", tech: null, timeline: tl([["waiting", iso(0, 13, 15), null]]), inspectionId: null },
    // Today - in progress (2)
    { id: "j4", vehicleId: "v2", customerId: "c2", complaint: "Pulls to the right, clunk over bumps", scheduledAt: iso(0, 8, 45), status: "in_progress", tech: "Luis", timeline: tl([["waiting", iso(0, 8, 45), null], ["accepted", iso(0, 8, 50), "Luis"], ["in_progress", iso(0, 9, 5), "Luis"]]), inspectionId: "i4" },
    { id: "j5", vehicleId: "v5", customerId: "c5", complaint: "Brakes squeaking", scheduledAt: iso(0, 11, 30), status: "in_progress", tech: "Ana", timeline: tl([["waiting", iso(0, 11, 30), null], ["accepted", iso(0, 11, 35), "Ana"], ["in_progress", iso(0, 11, 45), "Ana"]]), inspectionId: "i5" },
    // Today - completed (1) with full mixed inspection
    { id: "j6", vehicleId: "v4", customerId: "c4", complaint: "Annual inspection", scheduledAt: iso(0, 8, 15), status: "completed", tech: "Mike", timeline: tl([["waiting", iso(0, 8, 15), null], ["accepted", iso(0, 8, 20), "Mike"], ["in_progress", iso(0, 8, 30), "Mike"], ["inspection_complete", iso(0, 9, 40), "Mike"], ["customer_contacted", iso(0, 9, 45), "Mike"], ["approved", iso(0, 10, 5), null], ["completed", iso(0, 12, 0), "Mike"]]), inspectionId: "i6" },
    // Past completed inspections (previous weeks)
    { id: "j7", vehicleId: "v1", customerId: "c1", complaint: "Slow leak, right rear", scheduledAt: iso(-14, 9, 0), status: "completed", tech: "Sam", timeline: tl([["waiting", iso(-14, 9, 0), null], ["accepted", iso(-14, 9, 5), "Sam"], ["in_progress", iso(-14, 9, 15), "Sam"], ["inspection_complete", iso(-14, 10, 0), "Sam"], ["customer_contacted", iso(-14, 10, 10), "Sam"], ["approved", iso(-14, 10, 30), null], ["completed", iso(-14, 12, 0), "Sam"]]), inspectionId: "i7" },
    { id: "j8", vehicleId: "v6", customerId: "c6", complaint: "Front brakes grinding", scheduledAt: iso(-21, 8, 30), status: "completed", tech: "Mike", timeline: tl([["waiting", iso(-21, 8, 30), null], ["accepted", iso(-21, 8, 35), "Mike"], ["in_progress", iso(-21, 8, 45), "Mike"], ["inspection_complete", iso(-21, 9, 30), "Mike"], ["customer_contacted", iso(-21, 9, 35), "Mike"], ["approved", iso(-21, 10, 0), null], ["completed", iso(-21, 11, 30), "Mike"]]), inspectionId: "i8" },
    { id: "j9", vehicleId: "v8", customerId: "c8", complaint: "Alignment check", scheduledAt: iso(-7, 13, 0), status: "completed", tech: "Ana", timeline: tl([["waiting", iso(-7, 13, 0), null], ["accepted", iso(-7, 13, 5), "Ana"], ["in_progress", iso(-7, 13, 15), "Ana"], ["inspection_complete", iso(-7, 14, 0), "Ana"], ["customer_contacted", iso(-7, 14, 5), "Ana"], ["approved", iso(-7, 14, 20), null], ["completed", iso(-7, 15, 0), "Ana"]]), inspectionId: "i9" }
  ];

  function blankTires() {
    return { LF: { tread: null, status: null }, RF: { tread: null, status: null }, LR: { tread: null, status: null }, RR: { tread: null, status: null }, notes: "" };
  }

  var inspections = [
    { id: "i4", jobId: "j4", vehicleId: "v2", date: dateOnly(0), tech: "Luis",
      tires: blankTires(),
      brakes: { frontPadsMm: null, frontRotor: null, rearPadsMm: null, rearRotor: null },
      tpms: { status: null, tpmNumber: "" }, suspension: { status: null, items: { innerTieRod: false, outerTieRod: false, controlArm: false, shock: false, strut: false, other: false }, otherText: "" },
      alignment: { status: null, alg: null }, notes: "",
      recommended: { tires: null, alignment: null, tpms: null, brakes: null, suspension: null }, photos: [] },
    { id: "i5", jobId: "j5", vehicleId: "v5", date: dateOnly(0), tech: "Ana",
      tires: blankTires(),
      brakes: { frontPadsMm: null, frontRotor: null, rearPadsMm: null, rearRotor: null },
      tpms: { status: null, tpmNumber: "" }, suspension: { status: null, items: { innerTieRod: false, outerTieRod: false, controlArm: false, shock: false, strut: false, other: false }, otherText: "" },
      alignment: { status: null, alg: null }, notes: "",
      recommended: { tires: null, alignment: null, tpms: null, brakes: null, suspension: null }, photos: [] },
    // Full mixed inspection: G/Y/R results
    { id: "i6", jobId: "j6", vehicleId: "v4", date: dateOnly(0), tech: "Mike",
      tires: {
        LF: { tread: 4, status: "Y" }, RF: { tread: 3, status: "R" },
        LR: { tread: 7, status: "G" }, RR: { tread: 6, status: "G" },
        notes: "Front tires worn on outer edge; rear tires good."
      },
      brakes: { frontPadsMm: 3, frontRotor: "worn", rearPadsMm: 8, rearRotor: "good" },
      tpms: { status: "ok", tpmNumber: "" },
      suspension: { status: "ok", items: { innerTieRod: false, outerTieRod: false, controlArm: false, shock: false, strut: false, other: false }, otherText: "" },
      alignment: { status: "rec", alg: "89" },
      notes: "Front right tire below 3/32 - replace soon. Front brakes at 3mm, recommend replacement. Alignment recommended with new front tires.",
      recommended: { tires: "now", alignment: "soon", tpms: "ok", brakes: "now", suspension: "ok" }, photos: [] },
    { id: "i7", jobId: "j7", vehicleId: "v1", date: dateOnly(-14), tech: "Sam",
      tires: { LF: { tread: 8, status: "G" }, RF: { tread: 8, status: "G" }, LR: { tread: 5, status: "Y" }, RR: { tread: 2, status: "R" }, notes: "RR tire punctured beyond repair; replaced." },
      brakes: { frontPadsMm: 9, frontRotor: "good", rearPadsMm: 7, rearRotor: "good" },
      tpms: { status: "ok", tpmNumber: "" }, suspension: { status: "ok", items: { innerTieRod: false, outerTieRod: false, controlArm: false, shock: false, strut: false, other: false }, otherText: "" },
      alignment: { status: "ok", alg: null }, notes: "Replaced right rear tire.",
      recommended: { tires: "now", alignment: "ok", tpms: "ok", brakes: "ok", suspension: "ok" }, photos: [] },
    { id: "i8", jobId: "j8", vehicleId: "v6", date: dateOnly(-21), tech: "Mike",
      tires: { LF: { tread: 6, status: "G" }, RF: { tread: 6, status: "G" }, LR: { tread: 5, status: "Y" }, RR: { tread: 5, status: "Y" }, notes: "" },
      brakes: { frontPadsMm: 1, frontRotor: "replace", rearPadsMm: 6, rearRotor: "good" },
      tpms: { status: "ok", tpmNumber: "" }, suspension: { status: "ok", items: { innerTieRod: false, outerTieRod: false, controlArm: false, shock: false, strut: false, other: false }, otherText: "" },
      alignment: { status: "ok", alg: null }, notes: "Front pads metal-to-metal; replaced front pads and rotors.",
      recommended: { tires: "soon", alignment: "ok", tpms: "ok", brakes: "now", suspension: "ok" }, photos: [] },
    { id: "i9", jobId: "j9", vehicleId: "v8", date: dateOnly(-7), tech: "Ana",
      tires: { LF: { tread: 7, status: "G" }, RF: { tread: 7, status: "G" }, LR: { tread: 7, status: "G" }, RR: { tread: 7, status: "G" }, notes: "" },
      brakes: { frontPadsMm: 8, frontRotor: "good", rearPadsMm: 8, rearRotor: "good" },
      tpms: { status: "ok", tpmNumber: "" }, suspension: { status: "ok", items: { innerTieRod: false, outerTieRod: false, controlArm: false, shock: false, strut: false, other: false }, otherText: "" },
      alignment: { status: "rec", alg: "79" }, notes: "Steering wheel off-center; performed 4-wheel alignment.",
      recommended: { tires: "ok", alignment: "now", tpms: "ok", brakes: "ok", suspension: "ok" }, photos: [] }
  ];

  window.DVI_SEED = { techs: techs, customers: customers, vehicles: vehicles, jobs: jobs, inspections: inspections };
})();
