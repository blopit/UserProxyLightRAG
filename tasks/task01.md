To implement scope partitioning with LightRAG, and to accommodate searching by workspace, user, thread, etc., the best approach is to structure the API to handle a flexible and evolving scheme. Below is an updated version of your API that integrates the **Scope Resource Name (SRN)** system you described.

### API Changes

#### 1. SRN Format

* **Scheme Versioning**: You would use a URI/URN-inspired scheme with versioning. The canonical format you've proposed is:

```
1.<ws32>.<subject_type>.<subject_id>[.proj_<project>][.thr_<thread>][.top_<topic>]
```

* **Breaking down the segments**:

  * `1.` - This is a versioning prefix to indicate the scheme version, ensuring backwards compatibility.
  * `<ws32>` - A 32-character lowercase hex UUID without dashes (ensuring uniqueness and proper namespace partitioning).
  * `<subject_type>` - Type of the subject (e.g., `user`, `agent`, `workspace`, `contact`, `project`, `system`).
  * `<subject_id>` - The unique identifier for the subject (with safe characters: `[a-z0-9_-]{1,63}`).
  * Optional segments:

    * `.proj_<project>` - Project-specific context.
    * `.thr_<thread>` - Thread-specific context.
    * `.top_<topic>` - Topic-specific context.

* **Canonicalization Rules**:

  * Convert everything to lowercase.
  * Normalize Unicode to NFC (Canonical Composition).
  * Validate that the `ws32` part is a 32-character hex UUID (generated from UUIDv4, stripping dashes).
  * Each segment is capped at 63 characters to prevent overflow and allow compatibility with indexers.

#### 2. API Changes

You will need to update the search API to accept the new `SRN` format. Here’s an outline of the changes:

1. **Input Parameters**:

   * `SRN` or `scope_string`: Accepts a complete SRN string (e.g., `1.abc12345abcd12345abc1234567890ab.user.johndoe.proj_projectA.thr_discussionA.top_topicX`).
   * Alternatively, allow users to input individual components (e.g., workspace ID, subject type, and subject ID) as optional fields.

2. **Search by Scope**:

   * Use the full SRN to filter the data.
   * If users want to search by workspace, user, thread, or topic, decompose the SRN into individual fields. This allows flexibility in querying each part.

3. **New Query Structure** (Example for MongoDB or Elasticsearch-like query systems):

   * If the `SRN` is provided:

     ```json
     {
       "workspace": "abc12345abcd12345abc1234567890ab",
       "subject_type": "user",
       "subject_id": "johndoe",
       "project": "projectA",
       "thread": "discussionA",
       "topic": "topicX"
     }
     ```

   * If parts of the SRN are omitted, defaults could be applied (e.g., defaulting `workspace` or `subject_type` if not specified).

4. **Scope Validation**:

   * Before querying, validate the `SRN` format to ensure compliance with the new partitioning rules.
   * Ensure the segments do not exceed the defined character limits.
   * Validate the workspace ID (`ws32`) to be a valid 32-char hex UUID.

#### 3. Example API Flow

1. **User Input**:

   * A user submits a scope string: `1.abc12345abcd12345abc1234567890ab.user.johndoe.proj_projectA.thr_discussionA.top_topicX`.

2. **Canonicalization and Validation**:

   * The input string is parsed, and each segment is validated for compliance (e.g., workspace UUID, subject types).
   * The components are extracted into a structured form.

3. **Search Operation**:

   * The system queries the database using the extracted fields:

     ```json
     {
       "workspace": "abc12345abcd12345abc1234567890ab",
       "subject_type": "user",
       "subject_id": "johndoe",
       "project": "projectA",
       "thread": "discussionA",
       "topic": "topicX"
     }
     ```

4. **Result**:

   * The query returns the relevant data partitioned according to the workspace, user, thread, or topic.

#### 4. Future Evolution

* By using a **versioned scheme** (`1.`), you can later extend this format without breaking existing data.
* New segments or changes can be introduced in future versions (e.g., adding support for new subject types or context types like `location` or `event`).

### API Request Example

**POST Request**:

```json
{
  "scope": "1.abc12345abcd12345abc1234567890ab.user.johndoe.proj_projectA.thr_discussionA.top_topicX"
}
```

**Response**:

```json
{
  "data": [
    {
      "id": "123",
      "content": "Some message related to the topic"
    },
    {
      "id": "124",
      "content": "Another message in the same context"
    }
  ]
}
```

### 5. Considerations

* **Indexing**: Ensure indexes are created on the new scope fields for optimal search performance (e.g., `workspace`, `subject_type`, `subject_id`).
* **Backwards Compatibility**: Older data can remain unpartitioned, and new data can follow the SRN format. You can optionally migrate data as needed.

This new approach will help partition your data in a scalable way, enabling efficient queries while preserving flexibility for future enhancements.
