export default function Feedback() {
  return (
    <div className="min-h-screen bg-gray-100 flex items-center justify-center">
      <div className="bg-white shadow-xl rounded-2xl p-8 w-96">
        <h2 className="text-2xl font-bold mb-4">Submit Feedback</h2>

        <textarea
          placeholder="Write your feedback..."
          className="w-full border p-3 rounded-lg h-32"
        />

        <button className="w-full mt-4 bg-green-600 text-white py-2 rounded-lg hover:bg-green-700">
          Submit
        </button>
      </div>
    </div>
  );
}
